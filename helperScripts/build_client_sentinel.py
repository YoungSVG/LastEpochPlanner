"""Update verified Sentinel ability costs, timing and equipment requirements.

This does not convert specialization mutations, combo sequences or proc damage.
"""
import argparse
from copy import deepcopy
from pathlib import Path

from build_client_items import Properties, clean_number, read_json, write_json
from build_client_skills import cast_time, component, convert_skill, validate_sources


SKILLS = {"Rive1", "VoidCleave", "AbyssalEchoes", "DevouringOrb", "Anomaly"}


def rive_parts(prefabs, props, player_speed):
    """Keep each strike's timing and damage, without inventing a combo average."""
    parts = []
    for name, label in (("Rive1", "First strike"), ("Rive2", "Second strike"), ("Rive3", "Third strike")):
        converted = convert_skill(prefabs[name], props, player_speed)
        if converted["baseFlags"] != {"hit": True, "melee": True, "attack": True}:
            raise ValueError("Unexpected Rive strike flags")
        parts.append({"name": label, "castTime": converted["castTime"], "stats": converted["stats"]})
    return parts


def update_basics(existing, ability, player_speed, weapon_types):
    if existing["treeId"] != ability["playerAbilityID"]:
        raise ValueError("Sentinel skill tree identity changed")
    if ability.get("requiresDualWielding"):
        raise ValueError("Dual wield requirement needs explicit support")
    result = deepcopy(existing)
    result["castTime"] = cast_time(ability, player_speed)
    result["skillTypeTags"] = ability["tags"]
    stats = result["stats"]
    stats.pop("cost", None)
    if ability["manaCost"]:
        stats["cost"] = {"Mana": clean_number(ability["manaCost"])}
    stats.pop("cooldown", None)
    if ability["maxCharges"] > 0:
        if ability["chargesGainedPerSecond"] <= 0:
            raise ValueError("Ability charges do not regenerate")
        stats["cooldown"] = clean_number(1 / ability["chargesGainedPerSecond"])
    result["baseFlags"].pop("requiresShield", None)
    if ability.get("requiresSheild"):
        result["baseFlags"]["requiresShield"] = True
    result.pop("weaponTypes", None)
    if ability.get("requireWeaponType"):
        permitted = ability["permittedWeaponTypes"]
        if not permitted or any(key not in weapon_types for key in permitted):
            raise ValueError("Missing or unknown required weapon types")
        result["weaponTypes"] = {weapon_types[key]: True for key in permitted}
    return result


def build(source, core, baseline, output):
    manifest = read_json(source / "manifest.json")
    validate_sources(manifest, read_json(core / "manifest.json"))
    player_speed = component(read_json(source / "player-ability-use.json"),
                             "UsingAbilityPlayer")["baseUseSpeedMultiplier"]
    props = Properties(core)
    weapons = {row["baseTypeID"]: row["displayName"]
               for row in props.table("ItemList")["EquippableItems"] if row["isWeapon"]}
    skills = read_json(baseline)
    seen = set()
    prefabs = {}
    for row in manifest["tables"]:
        if row["class"] != "AbilityPrefab" or row.get("name") not in SKILLS | {"Rive2", "Rive3"}:
            continue
        prefab = read_json(source / row["path"])
        ability = prefab["ability"]
        name = ability["m_Name"]
        if name != row["name"] or name in seen:
            raise ValueError("Duplicate or mismatched Sentinel ability")
        seen.add(name)
        prefabs[name] = prefab
        if name in SKILLS:
            skills[name] = update_basics(skills[name], ability, player_speed, weapons)
    if seen != SKILLS | {"Rive2", "Rive3"}:
        raise ValueError("Missing priority Sentinel abilities")
    skills["Rive1"]["parts"] = rive_parts(prefabs, props, player_speed)
    write_json(output, skills)
    print(f"Updated {len(SKILLS)} Sentinel skills and three Rive strike definitions")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source", "core", "baseline", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    build(args.source, args.core, args.baseline, args.output)
