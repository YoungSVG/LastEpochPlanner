"""Regressions for the 1.5.2.2 prefab-to-planner skill conversion."""
import unittest
from copy import deepcopy
from unittest.mock import Mock

from build_client_skills import cast_time, convert_skill, validate_sources
from build_client_sentinel import rive_parts, update_basics


class SkillConversionTests(unittest.TestCase):
    def test_rive_parts_keep_third_strike_damage_and_timing_separate(self):
        prefabs = {}
        for index, (duration, speed, effectiveness) in enumerate(((0.75, 1.25, 1.25),
                                                               (0.75, 1.25, 1.25),
                                                               (0.699999988079071, 1, 2.5)), 1):
            name = f"Rive{index}"
            ability = {"m_Name": name, "abilityName": "Rive", "tags": 513,
                       "playerAbilityID": "sndr1", "useDuration": duration,
                       "speedMultiplier": speed, "channelled": 0, "instantCastForPlayer": 0,
                       "maxCharges": 0, "manaCost": 0, "attributeScaling": []}
            damage = {"damage": [2, 0, 0, 0, 0, 0, 0], "critChance": 0.05,
                      "critMultiplier": 2, "isHit": 1, "addedDamageScaling": effectiveness}
            prefabs[name] = {"ability": ability, "objects": [{"class": "DamageEnemyOnHit",
                             "data": {"damageTags": 512, "baseDamageStats": damage}}]}
        parts = rive_parts(prefabs, None, 1.100000023841858)
        self.assertEqual([1.25, 1.25, 2.5], [part["stats"]["damageEffectiveness"] for part in parts])
        self.assertEqual([0.5454545, 0.5454545, 0.6363636], [part["castTime"] for part in parts])
        self.assertEqual([2, 2, 2], [part["stats"]["melee_base_physical_damage"] for part in parts])
        self.assertEqual([5, 5, 5], [part["stats"]["critChance"] for part in parts])

    def test_sentinel_basics_keep_damage_and_require_the_native_weapon_types(self):
        existing = {"treeId": "v01cv", "baseFlags": {"melee": True, "hit": True},
                    "stats": {"melee_base_void_damage": 2, "damageEffectiveness": 4}}
        ability = {"playerAbilityID": "v01cv", "tags": 528, "useDuration": 2,
                   "speedMultiplier": 0.800000011920929, "manaCost": 15,
                   "maxCharges": 1, "chargesGainedPerSecond": 0.25,
                   "channelled": 0, "instantCastForPlayer": 0,
                   "requireWeaponType": 1, "permittedWeaponTypes": [12, 16]}
        weapons = {12: "Two-Handed Axe", 16: "Two-Handed Sword"}
        result = update_basics(existing, ability, 1.100000023841858, weapons)
        self.assertEqual(2.2727272, result["castTime"])
        self.assertEqual({"Mana": 15}, result["stats"]["cost"])
        self.assertEqual(4, result["stats"]["cooldown"])
        self.assertEqual(4, result["stats"]["damageEffectiveness"])
        self.assertEqual(2, result["stats"]["melee_base_void_damage"])
        self.assertEqual({name: True for name in weapons.values()}, result["weaponTypes"])
        self.assertNotIn("cost", existing["stats"])
        for permitted in ([], [999]):
            ability["permittedWeaponTypes"] = permitted
            with self.assertRaisesRegex(ValueError, "required weapon"):
                update_basics(existing, ability, 1.1, weapons)

    def test_sentinel_basics_remove_obsolete_cost_and_reject_wrong_tree(self):
        existing = {"treeId": "an0my", "baseFlags": {"spell": True},
                    "stats": {"cost": {"Mana": 99}, "cooldown": 99}}
        ability = {"playerAbilityID": "an0my", "tags": 272, "useDuration": 0.75,
                   "speedMultiplier": 1, "manaCost": 0, "maxCharges": 1,
                   "chargesGainedPerSecond": 0.08340000361204147,
                   "channelled": 0, "instantCastForPlayer": 0}
        result = update_basics(existing, ability, 1.100000023841858, {})
        self.assertNotIn("cost", result["stats"])
        self.assertEqual(11.99041, result["stats"]["cooldown"])
        ability["playerAbilityID"] = "wrong"
        with self.assertRaisesRegex(ValueError, "identity"):
            update_basics(existing, ability, 1.1, {})

    def test_equipment_requirements_keep_client_weapon_ids_and_shield_flag(self):
        ability = {"m_Name": "RadiantLance", "abilityName": "Radiant Lance", "tags": 258,
                   "playerAbilityID": "ra1an", "useDuration": 0.9, "speedMultiplier": 1,
                   "channelled": 0, "instantCastForPlayer": 0, "maxCharges": 0,
                   "manaCost": 24, "attributeScaling": [], "requiresSheild": 1}
        damage = {"damage": [0, 0, 0, 100, 0, 0, 0], "critChance": 0.05,
                  "critMultiplier": 2, "isHit": 1, "addedDamageScaling": 5}
        prefab = {"ability": ability, "objects": [{"class": "DamageEnemyOnHit",
                  "data": {"damageTags": 256, "baseDamageStats": damage}}]}
        skill = convert_skill(prefab, None, 1.1)
        self.assertTrue(skill["baseFlags"]["requiresShield"])
        self.assertEqual(1, skill["stats"]["damage_+%_final_per_uncapped_block_chance"])
        self.assertNotIn("shieldAttack", skill["baseFlags"])
        self.assertNotIn("weaponTypes", skill)
        ability.update(requiresSheild=0, requireWeaponType=1, permittedWeaponTypes=[6, 9])
        props = Mock()
        props.table.return_value = {"EquippableItems": [
            {"baseTypeID": 6, "displayName": "Dagger", "isWeapon": 1},
            {"baseTypeID": 9, "displayName": "One-Handed Sword", "isWeapon": 1},
            {"baseTypeID": 23, "displayName": "Bow", "isWeapon": 1}]}
        skill = convert_skill(prefab, props, 1.1)
        self.assertEqual({"Dagger": True, "One-Handed Sword": True}, skill["weaponTypes"])
        self.assertNotIn("requiresShield", skill["baseFlags"])
        for permitted in ([], [999]):
            ability["permittedWeaponTypes"] = permitted
            with self.assertRaisesRegex(ValueError, "required weapon"):
                convert_skill(prefab, props, 1.1)

    def test_source_fingerprints_reject_mixed_builds_with_the_same_version(self):
        core = {"clientVersion": "1.5.2.2", "unityVersion": "6000.4.8f1", "buildHash": "build-a",
                "sources": [{"path": path, "bytes": 123, "sha256": "a" * 64} for path in (
                    "GameAssembly.dll", "Last Epoch_Data/il2cpp_data/Metadata/global-metadata.dat",
                    "Last Epoch_Data/StreamingAssets/LEAssetBundles/PermaLoad.bundle")]}
        prefabs = deepcopy(core)
        # Separate bundles are expected; only overlapping sources must match.
        prefabs["sources"].append({"path": "skill.bundle", "bytes": 456, "sha256": "b" * 64})
        validate_sources(prefabs, core)
        for index in range(3):
            changed = deepcopy(prefabs)
            changed["sources"][index]["sha256"] = "c" * 64
            with self.assertRaisesRegex(ValueError, "fingerprints differ"):
                validate_sources(changed, core)
        for key in ("clientVersion", "unityVersion", "buildHash"):
            changed = deepcopy(prefabs)
            changed[key] = "another build"
            with self.assertRaisesRegex(ValueError, key):
                validate_sources(changed, core)
        changed = deepcopy(prefabs)
        changed["sources"].pop(0)
        with self.assertRaisesRegex(ValueError, "lack required"):
            validate_sources(changed, core)
        changed = deepcopy(prefabs)
        changed["sources"].append(changed["sources"][0])
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            validate_sources(changed, core)

    def test_player_speed_is_not_applied_to_a_minion(self):
        ability = {"useDuration": 0.6000000238418579, "speedMultiplier": 0.800000011920929,
                   "channelled": 0, "instantCastForPlayer": 0}
        self.assertEqual(0.75, cast_time(ability, 1))
        ability.update(useDuration=0.75, speedMultiplier=1)
        self.assertEqual(0.6818182, cast_time(ability, 1.100000023841858))

    def test_geyser_keeps_cold_damage_effectiveness_and_cooldown(self):
        # Relevant serialized fields from PrimalistElemental 02 Geyser.
        ability = {"m_Name": "PrimalistElemental 02 Geyser", "abilityName": "Geyser",
                   "tags": 260, "useDuration": 1.100000023841858, "speedMultiplier": 1,
                   "channelled": 0, "instantCastForPlayer": 0, "maxCharges": 1,
                   "chargesGainedPerSecond": 0.25, "manaCost": 0, "attributeScaling": []}
        damage = {"damage": [0, 0, 80, 0, 0, 0, 0], "critChance": 0.05000000074505806,
                  "critMultiplier": 2, "isHit": 1, "addedDamageScaling": 4}
        prefab = {"ability": ability, "objects": [{"class": "DamageEnemyOnHit",
                  "data": {"damageTags": 256, "baseDamageStats": damage}}]}
        skill = convert_skill(prefab, None, 1, minion=True)
        self.assertEqual(80, skill["stats"]["spell_base_cold_damage"])
        self.assertEqual(4, skill["stats"]["damageEffectiveness"])
        self.assertEqual(4, skill["stats"]["cooldown"])
        self.assertEqual(5, skill["stats"]["critChance"])
        self.assertEqual(1.1, skill["castTime"])
        self.assertTrue(skill["fromMinion"])
        self.assertNotIn("treeId", skill)
        self.assertEqual({"spell": True, "hit": True}, skill["baseFlags"])
        prefab["objects"].append(prefab["objects"][0])
        with self.assertRaisesRegex(ValueError, "Expected one DamageEnemyOnHit"):
            convert_skill(prefab, None, 1, minion=True)

    def test_unsupported_timing_fails_instead_of_guessing(self):
        ability = {"useDuration": 1, "speedMultiplier": 1, "channelled": 1, "instantCastForPlayer": 0}
        with self.assertRaisesRegex(ValueError, "timing"):
            cast_time(ability, 1)


if __name__ == "__main__":
    unittest.main()
