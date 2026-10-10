"""Regressions for the 1.5.2.2 prefab-to-planner skill conversion."""
import unittest

from build_client_skills import cast_time, convert_skill


class SkillConversionTests(unittest.TestCase):
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
