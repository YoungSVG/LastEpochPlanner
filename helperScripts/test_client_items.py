"""Regression cases for serialized item values and tooltip roll associations."""
import unittest

from build_client_items import Properties, tooltip, legacy_names, resolve_legacy_name_conflicts, unique_tooltip


class ItemConversionTests(unittest.TestCase):
    def test_dragonsong_speed_uses_gameplay_roll_instead_of_tooltip_slot(self):
        item = {"uniqueID": 243, "mods": [{} for _ in range(9)]}
        for index, prop in ((7, 2), (8, 3)):
            item["mods"][index] = {"property": prop, "tags": 8, "type": 1, "rollID": 3,
                                   "canRoll": 1, "specialTag": 0, "value": 0.11999999731779099,
                                   "maxValue": 0.17000000178813934}
        text = "+[12,17,7]% increased Attack and Cast Speed with Fire Skills"
        result = unique_tooltip(self.props, item, 2, text)
        self.assertEqual([("+(12-17)% increased Attack and Cast Speed with Fire Skills", 3, [3])], result)
        item["mods"][8]["rollID"] = 4
        with self.assertRaisesRegex(ValueError, "needs review"):
            unique_tooltip(self.props, item, 2, text)

    def test_anurok_resistances_keep_independent_player_and_minion_rolls(self):
        self.props.master[14] = {"displayAddedAsPercentage": 1}
        self.props.english["Descriptors"].update({"14,0,0,0": "Cold Resistance",
                                                  "14,8192,0,0": "Minion Cold Resistance"})
        item = {"uniqueID": 430, "mods": [{}, {}]}
        for tags, roll_id in ((0, 0), (8192, 1)):
            item["mods"].append({"property": 14, "tags": tags, "type": 0, "rollID": roll_id,
                                 "canRoll": 1, "specialTag": 0, "value": 0.5, "maxValue": 0.75})
        result = unique_tooltip(self.props, item, 1, "+[50,75,0]% Cold Resistance for you and your Minions")
        self.assertEqual([("+(50-75)% Cold Resistance", 0, [0]),
                          ("+(50-75)% Minion Cold Resistance", 1, [1])], result)

    def test_reused_current_name_is_not_installed_as_a_legacy_alias(self):
        bases = {
            "Roughspun Tunic": {"baseTypeID": 1, "subTypeID": 43, "legacyNames": ["Cloth Armor", "Older Tunic"]},
            "Cloth Armor": {"baseTypeID": 1, "subTypeID": 72},
        }
        conflicts = resolve_legacy_name_conflicts(bases)
        self.assertEqual(["Older Tunic"], bases["Roughspun Tunic"]["legacyNames"])
        self.assertEqual(43, conflicts[0]["oldSubTypeID"])
        self.assertEqual(72, conflicts[0]["currentSubTypeID"])
        self.assertEqual("Cloth Armor", conflicts[0]["legacyName"])
        self.assertEqual(conflicts, resolve_legacy_name_conflicts(bases))

    def test_renamed_base_keeps_old_names_across_updates(self):
        self.assertEqual(["Outcast Cage"], legacy_names("Pariah Shroud", "Outcast Cage", {}))
        self.assertEqual(["Outcast Cage"], legacy_names("Pariah Shroud", "Pariah Shroud", {"legacyNames": ["Outcast Cage"]}))
        self.assertEqual(["Pariah Shroud"], legacy_names("Outcast Cage", "Pariah Shroud", {"legacyNames": ["Outcast Cage"]}))
        self.assertEqual([], legacy_names("New Base", None, {}))

    def setUp(self):
        self.props = Properties.__new__(Properties)
        # Relevant flags and descriptor text from the 1.5.2.2 client.
        self.props.master = {
            7: {"roundingForAdded": 1},
            51: {"displayAddedAsPercentage": 1, "displayAddedAsTenthOfValue": 1,
                 "displayAsPercentageOf": 1},
            8: {"roundingForAdded": 1},
        }
        self.props.indexed = {98: {569: {}, 683: {}, 4: {}}}
        self.props.english = {"Descriptors": {
            "7,0,0,0": "Health",
            "51,0,0,1": "of Damage Leeched as Health",
            "8,0,0,0,6": "less Mana",
            "98,569,0,0,0": "Chance to Ignite on Hit per 10% uncapped Fire Resistance",
            "98,683,0,0,0": "Chance to inflict Bleed on hit per 1 Mana Cost",
            "98,4,0,0,0": "Bees Per 10 Seconds",
        }}

    def render(self, prop, low, high, tags=0, mode=0):
        return self.props.render({"property": prop, "tags": tags, "specialTag": 0, "extraTag": 0, "type": mode}, low, high)

    def test_chance_uses_percentage_units_despite_incomplete_display_flag(self):
        self.assertEqual("+(4-7)% Chance to Ignite on Hit per 10% uncapped Fire Resistance",
                         self.render(98, 0.03999999910593033, 0.07000000029802322, tags=569))
        self.assertEqual("+10% Chance to inflict Bleed on hit per 1 Mana Cost", self.render(98, 0.1, 0.1, tags=683))

    def test_fractional_minion_rate_is_not_a_probability(self):
        self.assertEqual("+(0.8-1.2) Bees Per 10 Seconds", self.render(98, 0.8, 1.2, tags=4))

    def test_integer_health_keeps_integer_roll_precision(self):
        self.assertEqual("{rounding:Integer}+(66-113) Health", self.render(7, 66, 113))

    def test_added_to_flag_does_not_invent_a_skill_level_label(self):
        self.props.master[7] = {"displayAsAddedTo": 1, "displayAddedAsPercentage": 1}
        self.props.english["Descriptors"]["7,0,0,0,2"] = "All Resistances"
        self.assertEqual("+10% to All Resistances", self.render(7, 0.1, 0.1))

    def test_leech_uses_tenths_of_percent(self):
        self.assertEqual("{rounding:Tenth}(1.5-2.5)% of Damage Leeched as Health", self.render(51, 0.15, 0.25))

    def test_negative_more_modifier_preserves_saved_roll_direction(self):
        self.assertEqual("(54-48)% less Mana", self.render(8, -0.54, -0.48, mode=2))

    def test_independent_roll_ids_are_retained_in_tooltip_order(self):
        line, rolls, all_rolls = tooltip("Gain [15,21,4] Mana and [180,330,5] Ward")
        self.assertEqual("Gain (15-21) Mana and (180-330) Ward", line)
        self.assertEqual([4, 5], rolls)
        self.assertEqual([4, 5], all_rolls)

    def test_constant_placeholder_does_not_consume_a_roll_position(self):
        line, rolls, _ = tooltip("Gain [10,10,0] Health and [15,21,4] Mana")
        self.assertEqual("Gain 10 Health and (15-21) Mana", line)
        self.assertEqual(4, rolls)

    def test_missing_descriptor_fails_instead_of_inventing_stat_text(self):
        with self.assertRaisesRegex(ValueError, "Missing client descriptor"):
            self.render(7, 10, 20, tags=8192)


if __name__ == "__main__":
    unittest.main()
