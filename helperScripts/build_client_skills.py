"""Convert the new 1.5 skills and Tide Elemental's attacks from exported prefabs."""
import argparse
from pathlib import Path

from build_client_items import Properties, read_json, write_json, clean_number


DAMAGE_TYPES = ("physical", "fire", "cold", "lightning", "necrotic", "void", "poison")
ATTRIBUTES = ("Strength", "Vitality", "Intelligence", "Dexterity", "Attunement")
NEW_SKILLS = {"Dreamslash", "RadiantLance", "PrimalistSummonElemental"}
MINION_SKILLS = {"PrimalistElemental 01 ElementalBolt": "TideElementalBolt",
                 "PrimalistElemental 02 Geyser": "TideElementalGeyser"}


def component(prefab, name):
    values = [row["data"] for row in prefab["objects"] if row["class"] == name]
    if len(values) != 1:
        raise ValueError(f"Expected one {name}, got {len(values)}")
    return values[0]


def cast_time(ability, actor_speed):
    speed = actor_speed * ability["speedMultiplier"]
    if speed <= 0 or ability["channelled"] or ability["instantCastForPlayer"]:
        raise ValueError("Unsupported ability timing configuration")
    return round(ability["useDuration"] / speed, 7)


def convert_skill(prefab, props, actor_speed, minion=False):
    ability = prefab["ability"]
    summon = ability["m_Name"] == "PrimalistSummonElemental"
    flags = {"minion": True} if summon else {}
    stats = {}
    if not summon:
        effect = component(prefab, "DamageEnemyOnHit")
        damage = effect["baseDamageStats"]
        if not damage["isHit"]:
            raise ValueError("Expected a hit-based ability")
        melee = bool(effect["damageTags"] & 512)
        spell = bool(effect["damageTags"] & 256)
        if melee == spell:
            raise ValueError("Expected exactly one melee or spell damage category")
        flags.update({"hit": True, **({"melee": True, "attack": True} if melee else {"spell": True})})
        stats.update({"damageEffectiveness": clean_number(damage["addedDamageScaling"]),
                      "base_critical_strike_multiplier_+": clean_number((damage["critMultiplier"] - 1) * 100),
                      "critChance": clean_number(damage["critChance"] * 100)})
        for damage_type, value in zip(DAMAGE_TYPES, damage["damage"], strict=True):
            if value:
                stats[f"{'melee' if melee else 'spell'}_base_{damage_type}_damage"] = clean_number(value)
    if ability["maxCharges"] > 0 and ability["chargesGainedPerSecond"] > 0:
        stats["cooldown"] = clean_number(1 / ability["chargesGainedPerSecond"])
    if ability["manaCost"]:
        stats["cost"] = {"Mana": clean_number(ability["manaCost"])}
    entry = {"name": ability["abilityName"], "skillTypeTags": ability["tags"],
             "castTime": cast_time(ability, actor_speed), "baseFlags": flags, "stats": stats}
    base_mods = []
    for attribute in ability["attributeScaling"]:
        for stat in attribute["stats"]:
            for mode, value in ((0, stat["addedValue"]), (1, stat["increasedValue"])):
                if value:
                    base_mods.append(props.render(stat, value, value, mode=mode) +
                                     " per player " + ATTRIBUTES[attribute["attribute"]])
            if stat["moreValues"]:
                raise ValueError("Attribute more-multipliers need explicit conversion")
    if base_mods:
        entry["baseMods"] = base_mods
    if minion:
        entry["fromMinion"] = True
    else:
        entry["treeId"] = ability["playerAbilityID"]
    if summon:
        entry["minionList"] = ["TideElemental"]
    return entry


def build(source, core, output):
    props = Properties(core)
    manifest = read_json(source / "manifest.json")
    prefabs = [read_json(source / row["path"]) for row in manifest["tables"] if row["class"] == "AbilityPrefab"]
    actors = [read_json(source / row["path"]) for row in manifest["tables"] if row["class"] == "ActorPrefab"]
    actors = [actor for actor in actors if actor["actor"]["m_Name"] == "Summoned Shaman Elemental"]
    if len(actors) != 1:
        raise ValueError("Expected the Tide Elemental actor")
    actor = actors[0]
    minion_speed = component(actor, "UsingMultipleAbilitiesAI")["baseUseSpeedMultiplier"]
    player_speed = component(read_json(source / "player-ability-use.json"), "UsingAbilityPlayer")["baseUseSpeedMultiplier"]
    skills = {}
    for prefab in prefabs:
        name = prefab["ability"]["m_Name"]
        if name in NEW_SKILLS:
            skills[name] = convert_skill(prefab, props, player_speed)
        elif name in MINION_SKILLS:
            skills[MINION_SKILLS[name]] = convert_skill(prefab, props, minion_speed, minion=True)
    if len(skills) != len(NEW_SKILLS) + len(MINION_SKILLS):
        raise ValueError("Missing new skill prefabs")
    minions = {"TideElemental": {"name": "Tide Elemental", "life": str(component(actor, "UnitHealth")["maxHealth"]),
                               "modList": [], "skillList": list(MINION_SKILLS.values())}}
    write_json(output / "skills.json", skills)
    write_json(output / "minions.json", minions)
    print(f"Converted {len(skills)} skill definitions and one minion")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source", "core", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    build(args.source, args.core, args.output)


if __name__ == "__main__":
    main()
