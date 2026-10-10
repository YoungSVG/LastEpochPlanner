"""Convert client item tables using the client's English modifier descriptors."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import re


# These probability/percentage stats have incomplete serialized display flags
# in 1.5.2.2. Keep explicit property IDs; never infer units from localized text.
PERCENT_PROPERTIES = {
    (98, tag, 0) for tag in (342, 405, 444, 448, 476, 504, 505, 512, 569, 581, 592, 625, 626, 676, 683)
} | {(58, ability, special) for ability, special in (
    (373, 1), (321, 1), (216, 6), (405, 2), (797, 1), (107, 4), (107, 3), (108, 2), (256, 3), (782, 8),
)} | {(130, tag, 0) for tag in (15, 16, 17)}


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def clean_number(value):
    # Serialized values are float32; remove their binary representation noise.
    return round(value, 5)


def number(value):
    return f"{clean_number(value):g}"


def unique_tooltip(props, item, description_id, text):
    """Use gameplay roll slots for the two verified client tooltip mismatches."""
    key = (item["uniqueID"], description_id)
    if key not in ((243, 2), (430, 1)):
        return [tooltip(text)]

    indices = (7, 8) if key == (243, 2) else (2, 3)
    expected = ((2, 8, 1, 3), (3, 8, 1, 3)) if key == (243, 2) else ((14, 0, 0, 0), (14, 8192, 0, 1))
    mods = [item["mods"][i] for i in indices]
    for mod, signature in zip(mods, expected):
        actual = (mod["property"], mod["tags"], mod["type"], mod["rollID"])
        if actual != signature or not mod["canRoll"] or mod["specialTag"] or mod.get("extraTag", 0):
            raise ValueError(f"Client unique roll correction needs review: {key}")

    if key == (430, 1):
        # The shared tooltip uses roll 0 for both actors; gameplay uses slots 0/1.
        if text != "+[50,75,0]% Cold Resistance for you and your Minions":
            raise ValueError(f"Client unique tooltip correction needs review: {key}")
        return [(props.render(m, m["value"], m["maxValue"]), m["rollID"], [m["rollID"]]) for m in mods]

    # Dragonsong's speed tooltip refers to slot 7, while both stats use slot 3.
    if any(clean_number(m["value"]) != 0.12 or clean_number(m["maxValue"]) != 0.17 for m in mods):
        raise ValueError(f"Client unique roll correction needs review: {key}")
    if text != "+[12,17,7]% increased Attack and Cast Speed with Fire Skills":
        raise ValueError(f"Client unique tooltip correction needs review: {key}")
    return [tooltip(text.replace("[12,17,7]", "[12,17,3]"))]


def plain(text):
    text = re.sub(r"</?(?:color|b|i|size|style)(?:=[^>]*)?>", "", text)
    return " ".join(text.replace("\\n", " ").split())


class Properties:
    def __init__(self, source):
        self.source = source
        manifest = read_json(source / "manifest.json")
        self.paths = {}
        for record in manifest["tables"]:
            self.paths.setdefault(record["class"], []).append(source / record["path"])
        self.english = read_json(source / "english.json")
        self.master = {p["property"]: p for p in self.table("PropertyList")["propertyInfoList"]}
        self.ability = {a["abilityID"]: a["properties"] for a in self.table("AbilityPropertyList")["list"]}
        self.indexed = {98: self.table("PlayerPropertyList")["list"],
                        130: self.table("IdolAltarPropertyList")["list"],
                        123: self.table("TrackerPropertyList")["list"]}
        self.ailments = {a["id"]: a for a in map(read_json, self.paths["Ailment"])}

    def table(self, name):
        paths = self.paths[name]
        if len(paths) != 1:
            raise ValueError(f"Expected a single {name} table")
        return read_json(paths[0])

    def definition(self, mod):
        prop, tags, special = mod["property"], mod["tags"], mod["specialTag"]
        if prop == 58:
            result = self.ability[tags][special]
        elif prop in self.indexed:
            result = self.indexed[prop][tags]
        elif prop == 120:
            # Effect-of-ailment descriptions are generated, not a master entry.
            result = {"displayAddedAsPercentage": 1}
        elif prop == 43 and self.ailments[special]["effectOfIncreasedEffectiveness"] == 1:
            result = self.master[59]
        else:
            result = self.master[prop]
        if (prop, tags, special) in PERCENT_PROPERTIES:
            result = dict(result, displayAddedAsPercentage=1)
        return result

    def render(self, mod, low, high, mode=None, custom=None):
        mode = mod.get("type", mod.get("modifierType")) if mode is None else mode
        info = self.definition(mod)
        negative = low < 0 and high < 0
        if mode == 0:
            kind = 2 if info.get("displayAsAddedTo") else 1 if info.get("displayAsPercentageOf") else 0
        elif mode == 1:
            kind = 0 if info.get("nameIncludesModifier") else 4 if negative else 3
        elif mode == 2:
            kind = 6 if negative else 5
        else:
            raise ValueError(f"Unsupported modifier type: {mode}")
        if custom is None:
            parts = [mod["property"], mod["tags"], mod["specialTag"]]
            key = ",".join(map(str, parts + [mod.get("extraTag", 0), kind]))
            description = self.english["Descriptors"].get(key)
            if description is None and not mod.get("extraTag", 0):
                description = self.english["Descriptors"].get(",".join(map(str, parts + [kind])))
            if description is None:
                raise ValueError(f"Missing client descriptor: {key}")
        else:
            description = custom
            if kind in (3, 4, 5, 6):
                prefix = {3: "increased", 4: "reduced", 5: "more", 6: "less"}[kind]
                if not description.lower().startswith(prefix + " "):
                    description = prefix + " " + description
        description = plain(description)
        if info.get("hideModifierValue"):
            return description
        percent = mode != 0 or info.get("displayAddedAsPercentage") or info.get("displayAsPercentageOf")
        factor = (10 if mode == 0 and info.get("displayAddedAsTenthOfValue") else 100) if percent else 1
        low, high = clean_number(low * factor), clean_number(high * factor)
        if negative and mode in (1, 2):
            low, high = -low, -high
        value = number(low) if low == high else f"({number(low)}-{number(high)})"
        if percent:
            value += "%"
        if mode == 0 and low > 0 and not info.get("dontDisplayPlus") and kind != 1:
            value = "+" + value
        if kind == 2:
            description = "to " + description
        line = value + " " + description
        if low != high:
            rounding = info.get("roundingForAdded", 0) if mode == 0 else 0 if mode == 1 else info.get("roundingForMore", 0)
            if mode == 2:
                for override in info.get("moreRoundingOverrides", []):
                    if override["specialTag"] == mod["specialTag"]:
                        rounding = override["roundingForMore"]
                        break
            precision = {0: 100, 1: 1, 2: 10, 3: 1000}[rounding] / factor
            candidates = {None: 100, "Integer": 1, "Tenth": 10, "Thousandth": 1000, "TenThousandth": 10000}
            for tag, scale in candidates.items():
                if "%" in line and scale >= 100:
                    scale /= 100
                if scale == precision:
                    return (f"{{rounding:{tag}}}" if tag else "") + line
            raise ValueError(f"Unsupported display rounding precision {precision}: {line}")
        return line


def tooltip(text):
    roll_ids = []
    def substitute(match):
        low, high, roll_id = match.groups()
        if float(low) == float(high):
            return low
        roll_ids.append(int(roll_id))
        return f"({low}-{high})"
    text = re.sub(r"\[\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*,\s*(\d+)\s*\]", substitute, text)
    text = re.sub(r"\(?\[\s*[\d.]+\s*,\s*c(?:\s*,\s*[\d.]+)?\s*\]%?\)?", "", text)
    # A line may contain multiple independent rolls. Keep that association
    # explicit for the importer instead of assigning all ranges to one roll.
    roll_id = roll_ids[0] if roll_ids and len(set(roll_ids)) == 1 else roll_ids or None
    return plain(text), roll_id, roll_ids


def legacy_names(name, previous_name, previous):
    """Preserve saved item names across repeated client updates."""
    names = set(previous.get("legacyNames", []))
    if previous_name:
        names.add(previous_name)
    return sorted(names - {name})


def resolve_legacy_name_conflicts(bases):
    """Current client names take precedence over aliases from older versions."""
    conflicts = []
    for name, base in bases.items():
        aliases = sorted(set(base.get("legacyNames", []) + base.get("legacyNameConflicts", [])))
        reused = []
        for alias in aliases:
            if alias in bases:
                reused.append(alias)
                conflicts.append({"legacyName": alias, "renamedBase": name,
                                  "oldBaseTypeID": base["baseTypeID"], "oldSubTypeID": base["subTypeID"],
                                  "currentBaseTypeID": bases[alias]["baseTypeID"],
                                  "currentSubTypeID": bases[alias]["subTypeID"]})
        remaining = [alias for alias in aliases if alias not in bases]
        if remaining:
            base["legacyNames"] = remaining
        else:
            base.pop("legacyNames", None)
        if reused:
            base["legacyNameConflicts"] = reused
        else:
            base.pop("legacyNameConflicts", None)
    return conflicts


def build_items(source, baseline, output):
    props = Properties(source)
    old_bases = read_json(baseline / "Bases/bases.json")
    old_by_id = {(b["baseTypeID"], b["subTypeID"]): b for b in old_bases.values()}
    old_names = {(b["baseTypeID"], b["subTypeID"]): name for name, b in old_bases.items()}
    bases = {}
    for base in props.table("ItemList")["EquippableItems"]:
        bid = base["baseTypeID"]
        if not base["displayName"]:
            continue
        for item in base["subItems"]:
            sid = item["subTypeID"]
            name = props.english["Item_Names"].get(f"Item_SubType_Name_{bid}_{sid}", item["displayName"] or item["name"])
            previous = old_by_id.get((bid, sid), {})
            entry = deepcopy(previous)
            names = legacy_names(name, old_names.get((bid, sid)), previous)
            if names:
                entry["legacyNames"] = names
            else:
                entry.pop("legacyNames", None)
            entry.update({"type": base["displayName"], "baseTypeID": bid, "subTypeID": sid,
                          "req": {"level": item["levelRequirement"]},
                          "affixEffectModifier": clean_number(base["affixEffectModifier"]),
                          "implicits": [props.render(mod, mod["implicitValue"], mod["implicitMaxValue"])
                                        for mod in item["implicits"]]})
            if base["isWeapon"]:
                # The planner's range unit starts at 1; client subtypes add range.
                entry["weapon"] = {"AttackRateBase": clean_number(item["attackRate"]),
                                   "Range": clean_number(1 + item["addedWeaponRange"])}
            if "Idol" in base["displayName"] and bid != 41:
                entry["width"], entry["height"] = base["gridSize"]["x"], base["gridSize"]["y"]
            if bid == 41 and "blockedCells" not in previous:
                raise ValueError(f"New altar needs a client layout: {sid}")
            if name in bases:
                raise ValueError(f"Duplicate base item name: {name}")
            bases[name] = entry

    name_conflicts = resolve_legacy_name_conflicts(bases)
    uniques = {}
    multi_roll_lines = []
    for item in props.table("UniqueList")["uniques"]:
        uid = item["uniqueID"]
        mods, roll_ids = [], []
        for display in item["tooltipEntries"]:
            index = display["modDisplay"]
            if index < 128:
                mod = item["mods"][index]
                if mod["hideInTooltip"]:
                    continue
                mods.append(props.render(mod, mod["value"], mod["maxValue"] if mod["canRoll"] else mod["value"]))
                roll_ids.append(mod["rollID"] if mod["canRoll"] else None)
            else:
                desc_id = index - 128
                data = item["tooltipDescriptions"][desc_id]
                if data["setRequirement"]:
                    continue
                text = props.english["Item_Names"].get(f"Unique_Tooltip_{desc_id}_{uid}", data["description"])
                for line, roll_id, all_rolls in unique_tooltip(props, item, desc_id, text):
                    mods.append(line)
                    roll_ids.append(roll_id)
                    if len(set(all_rolls)) > 1:
                        multi_roll_lines.append({"uniqueID": uid, "line": len(mods), "rollIds": all_rolls})
        uniques[str(uid)] = {
            "name": props.english["Item_Names"].get(f"Unique_Name_{uid}", item["displayName"] or item["name"]),
            "baseTypeID": item["baseType"], "subTypeID": item["subTypes"][0],
            "req": {"level": item["levelRequirement"]}, "mods": mods, "rollIds": roll_ids,
        }

    affixes = {}
    source_affixes = props.table("AffixList")
    for affix in source_affixes["singleAffixes"] + source_affixes["multiAffixes"]:
        aid = affix["affixId"]
        translations = props.english["Item_Affixes"]
        for tier_id, tier in enumerate(affix["tiers"]):
            entry = {"affix": translations.get(f"Item_Affix_{aid}_Title", affix["affixTitle"]),
                     "level": affix["levelRequirement"], "statOrderKey": aid, "statOrder": [aid],
                     "tier": tier_id, "type": "Prefix" if affix["type"] == 0 else "Suffix"}
            if affix["standardAffixEffectModifier"]:
                entry["standardAffixEffectModifier"] = clean_number(affix["standardAffixEffectModifier"])
            rolls = [tier] + tier["extraRolls"]
            for index, mod in enumerate(affix.get("affixProperties", [affix])):
                custom = None
                if not mod["useGeneratedNameForDisplayName"]:
                    custom = translations.get(f"Item_Affix_{aid}_Affix_{chr(65 + index)}")
                    if not custom:
                        custom = mod.get("modDisplayName") or translations.get(f"Item_Affix_{aid}_DisplayName") or affix["affixDisplayName"]
                roll = rolls[index]
                entry[str(index + 1)] = props.render(mod, roll["minRoll"], roll["maxRoll"], mode=mod["modifierType"], custom=custom)
            affixes[f"{aid}_{tier_id}"] = entry
    write_json(output / "Bases/bases.json", bases)
    write_json(output / "Uniques/uniques.json", uniques)
    write_json(output / "ModItem.json", affixes)
    write_json(output / "multi-roll-tooltip-lines.json", multi_roll_lines)
    write_json(output / "base-name-conflicts.json", name_conflicts)
    print({"bases": len(bases), "uniques": len(uniques), "affixTiers": len(affixes), "multiRollLines": len(multi_roll_lines)})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    build_items(args.source, args.baseline, args.output)


if __name__ == "__main__":
    main()
