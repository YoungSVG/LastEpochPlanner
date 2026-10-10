"""Export selected ability prefabs and their summoned actors from a client export."""
import argparse
import json
from pathlib import Path

from export_client import ClientExporter, soft_guid, write_json


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


class SkillExporter:
    def __init__(self, client, source):
        self.client = client
        self.source = source
        self.loaded = {}
        self.abilities = {}
        manifest = read_json(source / "manifest.json")
        if manifest["clientVersion"] != client.version:
            raise ValueError("Core export and requested client versions differ")
        for row in manifest["tables"]:
            if row["class"] == "Ability":
                self.abilities[row["pathId"]] = read_json(source / row["path"])
            elif row["class"] == "AbilityManager":
                manager = read_json(source / row["path"])
                self.ability_keys = {entry["key"]: entry["ability"]["m_PathID"]
                                     for entry in manager["keyedArray"]}

    def environment(self, bundle):
        if bundle not in self.loaded:
            self.loaded[bundle] = self.client.load(self.client.bundles / bundle)
        return self.loaded[bundle]

    def prefab(self, reference):
        guid = soft_guid(reference)
        bundle = self.client.index[guid]
        env = self.environment(bundle)
        targets = [asset.container[guid] for asset in env.assets if guid in asset.container]
        if len(targets) != 1:
            raise ValueError(f"Expected one prefab for {guid}")
        pending = [targets[0].deref()]
        seen, components, actors = set(), [], []
        while pending:
            owner_obj = pending.pop()
            identity = (owner_obj.assets_file.name, owner_obj.path_id)
            if identity in seen:
                continue
            seen.add(identity)
            owner = owner_obj.read()
            for entry in owner.m_Component:
                obj = entry.component.deref()
                if obj.type.name in ("Transform", "RectTransform"):
                    pending.extend(child.deref_parse_as_object().m_GameObject.deref()
                                   for child in obj.read().m_Children)
                elif obj.type.name == "MonoBehaviour":
                    name = self.client.script_class(obj)
                    if not name:
                        continue
                    data = obj.read_typetree()
                    components.append({"class": name, "pathId": obj.path_id,
                                       "owner": owner.m_Name, "data": data})
                    ref = data.get("ActorReference", {})
                    if ref.get("m_PathID"):
                        if ref["m_FileID"] != 0:
                            raise ValueError("External actor reference needs explicit resolution")
                        actor = obj.assets_file.objects[ref["m_PathID"]]
                        if self.client.script_class(actor) != "ActorData":
                            raise ValueError("Summon reference is not ActorData")
                        actors.append((actor.path_id, actor.read_typetree()))
        return {"guid": guid, "bundle": bundle, "objects": components}, actors

    def export(self, names):
        pending = []
        for name in names:
            matches = [key for key, value in self.abilities.items() if value["m_Name"] == name]
            if len(matches) != 1:
                raise ValueError(f"Expected one ability named {name}, got {len(matches)}")
            pending.extend(matches)
        seen_abilities, seen_actors = set(), set()
        while pending:
            key = pending.pop()
            if key in seen_abilities:
                continue
            seen_abilities.add(key)
            ability = self.abilities[key]
            prefab, actors = self.prefab(ability["abilityPrefabSoftRef"])
            write_json(self.client.output / f"abilities/{key}.json", {"ability": ability, **prefab})
            self.client.records.append({"class": "AbilityPrefab", "pathId": key,
                                        "name": ability["m_Name"], "path": f"abilities/{key}.json"})
            for actor_id, actor in actors:
                if actor_id in seen_actors:
                    continue
                seen_actors.add(actor_id)
                actor_prefab, nested = self.prefab(actor["ActorSoftRef"])
                if nested:
                    raise ValueError("Nested summoners need explicit export support")
                write_json(self.client.output / f"actors/{actor_id}.json", {"actor": actor, **actor_prefab})
                self.client.records.append({"class": "ActorPrefab", "pathId": actor_id,
                                            "name": actor["m_Name"], "path": f"actors/{actor_id}.json"})
                for component in actor_prefab["objects"]:
                    if component["class"] == "AbilityList":
                        data = component["data"]
                        for ref in data.get("abilities", []):
                            if ref["m_PathID"]:
                                pending.append(ref["m_PathID"])
                        pending.extend(self.ability_keys[ref["key"]] for ref in data.get("abilityRefs", []) if ref["key"])
        # The player and summoned actors can have different base use speeds.
        env = self.environment("PermaLoad.bundle")
        players = [obj for obj in env.objects if obj.type.name == "MonoBehaviour"
                   and obj.peek_name() == "MainPlayer"
                   and self.client.script_class(obj) == "ActorData"]
        if len(players) != 1:
            raise ValueError("Expected one MainPlayer actor definition")
        actor = players[0].read_typetree()
        player, _ = self.prefab(actor["ActorSoftRef"])
        player["objects"] = [obj for obj in player["objects"] if obj["class"] == "UsingAbilityPlayer"]
        if len(player["objects"]) != 1:
            raise ValueError("Expected one player ability-use component")
        write_json(self.client.output / "player-ability-use.json", player)
        self.client.records.append({"class": "PlayerAbilityUse", "path": "player-ability-use.json"})
        self.client.finish()
        print(f"Exported {len(seen_abilities)} abilities and {len(seen_actors)} actors")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("game", "assemblies", "source", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--client-version", required=True)
    parser.add_argument("--ability", action="append", required=True)
    args = parser.parse_args()
    index = read_json(args.source / "bundle-index.json")
    client = ClientExporter(args.game, args.assemblies, args.output, args.client_version, index)
    SkillExporter(client, args.source).export(args.ability)


if __name__ == "__main__":
    main()
