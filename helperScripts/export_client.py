"""Read a local Last Epoch client into an auditable, intermediate data export.

Requires UnityPy and TypeTreeGeneratorAPI. Supply Cpp2IL dummy assemblies generated
with attributeanalyzer; without SerializeField attributes, tables are incomplete.
This script never writes inside the game installation and does not read saves.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path

import UnityPy
from UnityPy.helpers.TypeTreeGenerator import TypeTreeGenerator


CORE_CLASSES = {
    "AbilityPropertyList", "PropertyList", "PlayerPropertyList", "SetBonusesList",
    "UniqueList", "ExtraStatData", "ItemList", "AffixList", "CharacterClass",
    "GearSpriteList", "GlobalTreeData", "PassivePanelData", "SkillTreeData",
    "IdolAltarPropertyList", "TrackerPropertyList", "Ability", "AbilityManager", "Ailment",
}


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def soft_guid(ref):
    value = ref["guid"]
    return f"{value['_0']:016x}{value['_1']:016x}"


def index_bundle(path):
    env = UnityPy.load(str(path))
    # Environment.container resolves every preload dependency. Read the local
    # container keys directly to avoid repeatedly loading the permanent bundle.
    return path.name, sorted({key for asset in env.assets for key in asset.container})


class ClientExporter:
    def __init__(self, game, assemblies, output, version, index=None):
        self.game = game.resolve()
        self.data = self.game / "Last Epoch_Data"
        self.bundles = self.data / "StreamingAssets" / "LEAssetBundles"
        self.output = output.resolve()
        if self.output.is_relative_to(self.game):
            raise ValueError("Export output must be outside the game installation")
        resources = UnityPy.load(str(self.data / "resources.assets"))
        self.unity_version = next(iter(resources.assets)).unity_version
        if version.encode("ascii") not in (self.data / "globalgamemanagers").read_bytes():
            raise ValueError("Requested client version is not present in globalgamemanagers")
        self.version = version
        self.generator = TypeTreeGenerator(self.unity_version)
        self.generator.load_local_dll_folder(str(assemblies.resolve()))
        self.records = []
        self.used_sources = {self.data / "globalgamemanagers", self.game / "GameAssembly.dll",
                             self.data / "il2cpp_data/Metadata/global-metadata.dat"}
        self.core = {}
        self.index = index or {}

    def load(self, path):
        self.used_sources.add(path)
        self.used_sources.add(self.bundles / "monoscripts.bundle")
        inputs = [str(path), str(self.bundles / "monoscripts.bundle")]
        if path.parent == self.data:
            inputs.append(str(self.data / "globalgamemanagers.assets"))
            self.used_sources.add(self.data / "globalgamemanagers.assets")
        env = UnityPy.load(*inputs)
        env.typetree_generator = self.generator
        return env

    def build_index(self):
        reuse_index = bool(self.index)
        name, keys = index_bundle(self.bundles / "PermaLoad.bundle")
        for key in keys:
            self.index.setdefault(key, name)
        if reuse_index:
            write_json(self.output / "bundle-index.json", self.index)
            return
        paths = sorted(self.bundles.glob("assets_*.bundle"))
        with ThreadPoolExecutor(max_workers=4) as pool:
            for count, (bundle, keys) in enumerate(pool.map(index_bundle, paths), 1):
                for key in keys:
                    if key in self.index and self.index[key] != bundle:
                        raise ValueError(f"Duplicate asset GUID: {key}")
                    self.index[key] = bundle
                if count % 1000 == 0:
                    print(f"Indexed {count}/{len(paths)} bundles", flush=True)
        write_json(self.output / "bundle-index.json", self.index)

    @staticmethod
    def script_class(obj):
        script = obj.parse_monobehaviour_head().m_Script
        return script.deref_parse_as_object().m_ClassName if script.path_id else ""

    def export_core(self):
        for source in (self.data / "resources.assets", self.bundles / "PermaLoad.bundle"):
            env = self.load(source)
            for obj in env.objects:
                if obj.type.name != "MonoBehaviour":
                    continue
                name = self.script_class(obj)
                if name not in CORE_CLASSES:
                    continue
                data = obj.read_typetree()  # Strict byte-count validation stays enabled.
                key = f"{name}/{obj.path_id}"
                relative = f"core/{key}.json"
                write_json(self.output / relative, data)
                self.records.append({"path": relative, "class": name, "name": data["m_Name"],
                                     "source": str(source.relative_to(self.game)).replace("\\", "/"),
                                     "pathId": obj.path_id})
                self.core.setdefault(name, []).append(data)
            print(f"Exported tables from {source.name}", flush=True)
        required = CORE_CLASSES - {"SkillTreeData"}
        missing = required - self.core.keys()
        if missing:
            raise ValueError(f"Missing core tables: {sorted(missing)}")

    def export_skill_catalog(self):
        # The catalog itself is a soft-loaded asset. Locate it by serialized
        # object name, without depending on a patch-specific bundle hash.
        bundles = sorted(set(self.index.values()))
        known = self.index.get("0ba90fcd1f319ef43a541073459ecb23")
        if known:
            bundles.remove(known)
            bundles.insert(0, known)
        for bundle in bundles:
            path = self.bundles / bundle
            env = UnityPy.load(str(path))
            for obj in env.objects:
                if obj.type.name == "MonoBehaviour" and obj.peek_name() == "SkillTreeData":
                    env = self.load(path)
                    target = next(o for o in env.objects if o.path_id == obj.path_id)
                    data = target.read_typetree()
                    self.core["SkillTreeData"] = [data]
                    write_json(self.output / "skill-tree-catalog.json", data)
                    return
        raise ValueError("SkillTreeData catalog not found")

    def transform_chain(self, game_object):
        for component in game_object.read().m_Component:
            target = component.component.deref()
            if target.type.name not in ("RectTransform", "Transform"):
                continue
            result = []
            seen = set()
            while target.path_id not in seen:
                seen.add(target.path_id)
                data = target.read_typetree()
                owner = target.read().m_GameObject.deref_parse_as_object()
                data["gameObjectName"] = owner.m_Name
                data["activeSelf"] = bool(owner.m_IsActive)
                result.append(data)
                parent = target.read().m_Father
                if not parent.path_id:
                    break
                target = parent.deref()
            return result
        raise ValueError("Tree node has no transform")

    def export_trees(self):
        refs = []
        for cls in self.core["SkillTreeData"][0]["classSkillTrees"]:
            refs.extend((cls["characterClass"], "skill", entry["tree"])
                        for entry in cls["trees"])
        for cls in self.core["PassivePanelData"][0]["classResources"]:
            refs.append((cls["classId"], "passive", cls["passiveTree"]))
            refs.extend((cls["classId"], "passiveNodes", ref) for ref in cls["masteryNodes"])
        for class_id, kind, ref in refs:
            guid = soft_guid(ref)
            bundle = self.index[guid]
            env = self.load(self.bundles / bundle)
            objects = {o.path_id: o for o in env.objects}
            records = []
            for obj in list(objects.values()):
                if obj.type.name != "MonoBehaviour":
                    continue
                name = self.script_class(obj)
                if "Tree" not in name and "Node" not in name and name != "Image":
                    continue
                data = obj.read_typetree()
                record = {"id": obj.path_id, "class": name, "data": data}
                if "id" in data and "maxPoints" in data:
                    record["transforms"] = self.transform_chain(objects[data["m_GameObject"]["m_PathID"]])
                records.append(record)
            externals = {asset.name: [e.path for e in asset.externals] for asset in env.assets}
            write_json(self.output / f"trees/{guid}.json", {
                "bundle": bundle, "guid": guid, "classId": class_id, "kind": kind,
                "externals": externals, "objects": records,
            })
        print(f"Exported {len(refs)} tree resources", flush=True)

    def finish(self):
        sources = []
        for path in sorted(self.used_sources):
            with path.open("rb") as stream:
                digest = hashlib.file_digest(stream, "sha256").hexdigest()
            sources.append({"path": path.relative_to(self.game).as_posix(),
                            "bytes": path.stat().st_size, "sha256": digest})
        manifest = {"schemaVersion": 1, "clientVersion": self.version,
                    "unityVersion": self.unity_version,
                    "buildHash": (self.data / "build_hash.txt").read_text().strip(),
                    "sources": sources, "tables": self.records,
                    "counts": {key: len(value) for key, value in sorted(self.core.items())}}
        write_json(self.output / "manifest.json", manifest)
        print("Wrote source manifest", flush=True)

    def export_localization(self):
        folder = self.data / "StreamingAssets/aa/StandaloneWindows64"
        paths = [folder / "localization-assets-shared_assets_all.bundle",
                 folder / "localization-string-tables-english(en)_assets_all.bundle"]
        tables = {}
        for path in paths:
            self.used_sources.add(path)
            env = UnityPy.load(str(path))
            for obj in env.objects:
                if obj.type.name == "MonoBehaviour":
                    # Addressable string tables retain their serialized type trees.
                    data = obj.read_typetree()
                    if "m_Entries" in data or "m_TableData" in data:
                        if obj.path_id in tables:
                            raise ValueError(f"Duplicate localization object: {obj.path_id}")
                        tables[obj.path_id] = data
        english = {}
        orphaned = []
        conflicts = []
        for table in tables.values():
            if "m_TableData" not in table:
                continue
            if table["m_LocaleId"]["m_Code"] != "en":
                raise ValueError("Expected English client localization")
            shared = tables[table["m_SharedData"]["m_PathID"]]
            keys = {entry["m_Id"]: entry["m_Key"] for entry in shared["m_Entries"]}
            values = {}
            ambiguous = set()
            for entry in table["m_TableData"]:
                if entry["m_Id"] not in keys:
                    # Unity tables can retain translations for deleted shared keys.
                    # They cannot be addressed by a current localization key.
                    orphaned.append({"table": table["m_Name"], "id": entry["m_Id"]})
                    continue
                key = keys[entry["m_Id"]]
                if key in ambiguous:
                    continue
                if key in values and values[key] != entry["m_Localized"]:
                    conflicts.append({"table": table["m_Name"], "key": key,
                                      "values": [values.pop(key), entry["m_Localized"]]})
                    ambiguous.add(key)
                    continue
                values[key] = entry["m_Localized"]
            english[table["m_Name"].removesuffix("_en")] = values
        required = {"Item_Names", "Item_Affixes", "Properties", "Descriptors", "Abilities", "Skills", "Ailments"}
        if not required.issubset(english):
            raise ValueError(f"Missing localization tables: {sorted(required - english.keys())}")
        write_json(self.output / "english.json", english)
        write_json(self.output / "orphaned-localization-entries.json", orphaned)
        # Do not choose arbitrary translations for ambiguous keys. Converters
        # can use the owning asset's fallback text and report those cases.
        write_json(self.output / "conflicting-localization-entries.json", conflicts)
        print(f"Exported {len(english)} English localization tables", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game", type=Path, required=True)
    parser.add_argument("--assemblies", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--client-version", required=True)
    parser.add_argument("--index", type=Path, help="Reuse a GUID-to-bundle index for the same client")
    args = parser.parse_args()
    index = json.loads(args.index.read_text(encoding="utf-8")) if args.index else None
    exporter = ClientExporter(args.game, args.assemblies, args.output, args.client_version, index)
    exporter.build_index()
    exporter.export_core()
    exporter.export_skill_catalog()
    exporter.export_trees()
    exporter.export_localization()
    exporter.finish()


if __name__ == "__main__":
    main()
