"""Convert a strict client export into planner tree data, preserving node IDs."""
import argparse
from copy import deepcopy
import json
from pathlib import Path

from export_client import soft_guid, write_json


CLASS_NAMES = {0: "Primalist", 1: "Mage", 2: "Sentinel", 3: "Acolyte", 4: "Rogue"}
ATTRIBUTE_NAMES = {"Strength": "Str", "Dexterity": "Dex", "Intelligence": "Int",
                   "Attunement": "Att", "Vitality": "Vit"}


def build_trees(source, baseline, output):
    manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    ability_records = {record["pathId"]: record for record in manifest["tables"] if record["class"] == "Ability"}
    catalog = json.loads((source / "skill-tree-catalog.json").read_text(encoding="utf-8"))
    skill_resources = {soft_guid(entry["tree"]): entry for cls in catalog["classSkillTrees"] for entry in cls["trees"]}
    core = {}
    for record in manifest["tables"]:
        if record["class"] in ("CharacterClass", "PassivePanelData", "GlobalTreeData"):
            core.setdefault(record["class"], []).append(json.loads((source / record["path"]).read_text(encoding="utf-8")))
    panels = {entry["classId"]: entry for entry in core["PassivePanelData"][0]["classResources"]}
    global_data = core["GlobalTreeData"][0]
    skill_rules = {tree["treeID"]: {n["id"]: n for n in tree["nodes"]} for tree in global_data["skillTrees"]}
    passive_rules = {("Sentinel" if tree["name"] == "Knight" else tree["name"]):
                     {n["id"]: n for n in tree["nodes"]} for tree in global_data["passiveTrees"]}
    old_trees = {cid: json.loads((baseline / f"tree_{cid}.json").read_text(encoding="utf-8")) for cid in CLASS_NAMES}
    trees = {}
    icon_sources = {}
    changes = {"newNodes": [], "removedNodes": [], "changedStats": [], "changedRequirements": [], "newSkillTrees": []}
    for cid, old in old_trees.items():
        headers = {key: deepcopy(node) for key, node in old["nodes"].items()
                   if key == CLASS_NAMES[cid] or node.get("isAscendancyStart")}
        trees[cid] = {"nodes": headers, "classes": deepcopy(old["classes"])}
        cls = next(entry for entry in core["CharacterClass"] if entry["classID"] == cid)
        for key in list(trees[cid]["classes"][0]):
            source_key = next(("base" + attr for attr, abbr in ATTRIBUTE_NAMES.items() if key == "base" + abbr), key)
            if source_key in cls:
                trees[cid]["classes"][0][key] = cls[source_key]
        for entry in panels[cid]["data"]:
            name = entry["name"].split("_", 1)[1]
            name = next((key for key in headers if key.replace(" ", "").lower() == name.replace("_", "").lower()), name)
            if name in headers and entry["isMastery"]:
                headers[name]["stats"] = entry["bonusFallbackText"]
            if name in headers:
                icon_sources[name] = {"classId": cid, "oldIcon": headers[name]["icon"],
                                      "bundle": "PermaLoad.bundle", "sprite": {"m_FileID": 0, "m_PathID": 0},
                                      "softRef": entry["icon"], "externals": {}, "logicalSize": 64}
        for node in headers.values():
            node["in"] = []
            node["out"] = []

    for path in sorted((source / "trees").glob("*.json")):
        resource = json.loads(path.read_text(encoding="utf-8"))
        if resource["kind"] == "passive":
            continue
        cid = resource["classId"]
        objects = {record["id"]: record for record in resource["objects"]}
        passive = resource["kind"] == "passiveNodes"
        if passive:
            tree_id = CLASS_NAMES[cid]
        else:
            roots = [r for r in objects.values() if "treeID" in r["data"] and "nodeList" in r["data"]]
            if len(roots) != 1:
                raise ValueError(f"Expected one tree root in {path.name}")
            tree_id = roots[0]["data"]["treeID"]
            ability_record = ability_records[skill_resources[resource["guid"]]["ability"]["m_PathID"]]
            ability = json.loads((source / ability_record["path"]).read_text(encoding="utf-8"))
            skills = trees[cid]["classes"][0]["skills"]
            if not any(skill["treeId"] == tree_id for skill in skills):
                skills.append({"name": ability["m_Name"], "label": ability["abilityName"], "treeId": tree_id})
        if passive:
            nodes = [r for r in objects.values() if r["class"] == "SkillTreeNode" and r["data"]["nodeName"]
                     and all(t["activeSelf"] for t in r["transforms"])]
        else:
            active_ids = {ref["m_PathID"] for ref in roots[0]["data"]["nodeList"]}
            nodes = [r for r in objects.values() if r["id"] in active_ids]
            if len(nodes) != len(active_ids):
                raise ValueError(f"Missing active tree nodes in {path.name}")
        node_ids = {r["id"]: f"{tree_id}-{r['data']['id']}" for r in nodes}
        rules = (passive_rules if passive else skill_rules)[tree_id]
        for record in nodes:
            data = record["data"]
            rule = rules[data["id"]]
            key = node_ids[record["id"]]
            previous = old_trees[cid]["nodes"].get(key)
            if key in trees[cid]["nodes"]:
                raise ValueError(f"Duplicate node ID {key}")
            stats, fixed = [], []
            for stat in data["stats"]:
                text = stat["value"] + " " + stat["statName"]
                (fixed if stat["noScaling"] else stats).append(text)
            node = {
                "skill": key, "name": data["nodeName"],
                "icon": previous["icon"] if previous else "",
                "x": previous["x"] if previous else 0,
                "y": previous["y"] if previous else 0,
                "maxPoints": rule["maxPoints"], "mastery": rule["requiredMastery"],
                "masteryRequirement": rule["masteryRequirement"],
                "stats": stats, "notScalingStats": fixed,
                "noScalingPointThreshold": data["noScalingPointThreshold"],
                "in": [], "reqPoints": [], "out": [],
            }
            for req in rule["requirements"]:
                node["in"].append(f"{tree_id}-{req['nodeID']}")
                node["reqPoints"].append(req["requirement"])
            if not node["in"] and (passive or data["id"] == 0):
                node["in"] = [CLASS_NAMES[cid]]
                node["reqPoints"] = [1]
            if not passive:
                position = record["transforms"][0]["m_AnchoredPosition"]
                node["x"], node["y"] = round(position["x"] * 0.8, 5), round(-position["y"] * 0.8, 5)
            if data["description"]:
                node["description"] = [data["description"]]
            if data["altText"]:
                node["reminderText"] = [data["altText"]]
            trees[cid]["nodes"][key] = node
            if previous is None:
                changes["newNodes"].append(key)
            else:
                if node["stats"] != previous["stats"] or node["notScalingStats"] != previous.get("notScalingStats", []):
                    changes["changedStats"].append(key)
                if any(node[field] != previous[field] for field in ("maxPoints", "mastery", "masteryRequirement", "in", "reqPoints")):
                    changes["changedRequirements"].append(key)
            image_id = data["icon"]["m_PathID"]
            if not image_id and data["treeNode"]["m_PathID"]:
                view = objects[data["treeNode"]["m_PathID"]]["data"]
                image_id = view["_nodeImage"]["m_PathID"]
            if image_id:
                image = objects[image_id]["data"]
                icon_sources[key] = {"classId": cid, "oldIcon": node["icon"], "bundle": resource["bundle"],
                                     "sprite": image["m_Sprite"], "softRef": image["m_SpriteSoftRef"],
                                     "externals": resource["externals"], "logicalSize": 62 if rule["maxPoints"] == 0 else 42}

    for cid, tree in trees.items():
        for key, node in tree["nodes"].items():
            for parent in node["in"]:
                if parent not in tree["nodes"]:
                    raise ValueError(f"Missing prerequisite {parent} for {key}")
                tree["nodes"][parent]["out"].append(key)
        changes["removedNodes"].extend(sorted(set(old_trees[cid]["nodes"]) - set(tree["nodes"])))
        existing_skills = {s["treeId"] for s in old_trees[cid]["classes"][0]["skills"]}
        actual_skills = {key.rsplit("-", 1)[0] for key in tree["nodes"] if key.endswith("-0") and not key.startswith(CLASS_NAMES[cid])}
        changes["newSkillTrees"].extend(sorted(actual_skills - existing_skills))
        tree["classes"][0]["skills"].sort(key=lambda entry: entry["label"].lower())
        write_json(output / f"tree_{cid}.json", tree)
    write_json(output / "icon-sources.json", icon_sources)
    write_json(output / "changes.json", changes)
    print({key: len(value) for key, value in changes.items()})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    build_trees(args.source, args.baseline, args.output)


if __name__ == "__main__":
    main()
