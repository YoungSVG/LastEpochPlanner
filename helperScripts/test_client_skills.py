"""Regressions for the 1.5.2.2 prefab-to-planner skill conversion."""
import unittest
from copy import deepcopy
from unittest.mock import Mock

from build_client_skills import cast_time, convert_skill, validate_sources


class SkillConversionTests(unittest.TestCase):
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
