-- Client specialization lines whose meaning depends on the owning node.
-- Keep the exact client text as the key so changed descriptions need review.
local mod = ...
return {
	["ra1an-21"] = {
		["+12% Damage"] = { mod("Damage", "MORE", 12) },
	},
	["ra1an-14"] = {
		["+1 Lightning Spell Damage per 300 Block Effectiveness"] = {
			mod("LightningMin", "BASE", 1, ModFlag.Spell, 0, { type = "PerStat", stat = "BlockEffectiveness", div = 300, continuous = true }),
			mod("LightningMax", "BASE", 1, ModFlag.Spell, 0, { type = "PerStat", stat = "BlockEffectiveness", div = 300, continuous = true }),
		},
	},
	["ra1an-32"] = {
		[" No Longer Requires Shield"] = {
			mod("Condition:RadiantLanceNoShield", "FLAG", true),
		},
		["+1% Damage per 25 Max Mana"] = {
			mod("Damage", "MORE", 1, 0, 0, { type = "PerStat", stat = "Mana", div = 25, continuous = true }),
		},
		-- The condition above also disables the skill's base block multiplier.
		[" No Damage Gain from Block Chance"] = {},
	},
}
