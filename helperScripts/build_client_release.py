"""Assemble client skill/tree exports into planner files without switching versions."""
import argparse
from pathlib import Path
import re

from build_client_items import read_json, write_json


def build(baseline, trees, skills, icons, output):
    definitions = read_json(baseline / "Data/skills.json")
    definitions.update(read_json(skills / "skills.json"))
    minions = read_json(baseline / "Data/minions.json")
    minions.update(read_json(skills / "minions.json"))
    node_icons = read_json(icons / "node-icons.json")
    registered_icons = set(re.findall(r"client_[a-f0-9]+", (baseline / "TreeData/ClientSprites.lua").read_text(encoding="utf-8")))
    compiled = {}
    for index in range(5):
        name = f"tree_{index}.json"
        tree = read_json(trees / name)
        for key, node in tree["nodes"].items():
            icon = node_icons.get(key)
            if icon not in registered_icons:
                raise ValueError(f"Missing installed client icon for {key}")
            node["icon"] = icon
            for neighbour in node.get("in", []) + node.get("out", []):
                if neighbour not in tree["nodes"]:
                    raise ValueError(f"Missing neighbour {neighbour} of {key}")
        for character in tree["classes"]:
            for ability in character.get("skills", []):
                skill = definitions.get(ability["name"])
                if not skill or skill.get("treeId") != ability["treeId"]:
                    raise ValueError(f"Missing matching skill definition for {ability['name']}")
        compiled[name] = tree
    for name, minion in minions.items():
        for skill in minion.get("skillList", []):
            # The existing non-attacking Rogue Decoy uses this empty slot.
            if skill != "NullAbility" and skill not in definitions:
                raise ValueError(f"Missing minion skill {name}/{skill}")
    # Validate all relationships before writing anything. The metadata contains
    # shared rendering geometry, not client skill or passive balance values.
    metadata = (baseline / "TreeData/1_4/tree.lua").read_text(encoding="utf-8")
    for name, tree in compiled.items():
        write_json(output / "TreeData/1_5" / name, tree)
    (output / "TreeData/1_5/tree.lua").write_text(metadata, encoding="utf-8")
    write_json(output / "Data/skills.json", definitions)
    write_json(output / "Data/minions.json", minions)
    print(f"Assembled {sum(len(tree['nodes']) for tree in compiled.values())} nodes and {len(definitions)} skills")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("baseline", "trees", "skills", "icons", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    build(args.baseline, args.trees, args.skills, args.icons, args.output)


if __name__ == "__main__":
    main()
