-- Client specialization lines whose meaning depends on the owning node.
-- Keep the exact client text as the key so changed descriptions need review.
local mod = ...
return {
	-- RiveTree.updateMutator, client 1.5.2.2: bonuses target individual strikes.
	["sndr1-15"] = {
		["+10% First And Second Strike Attack Speed"] = {
			mod("Speed", "INC", 10, 0, 0, { type = "SkillPart", skillPartList = { 1, 2 } }),
		},
	},
	["sndr1-16"] = {
		["+1% First And Second Strike Base Crit Chance"] = {
			mod("CritChance", "BASE", 1, 0, 0, { type = "SkillPart", skillPartList = { 1, 2 } }),
		},
		["+2% Third Strike Base Crit Chance"] = {
			mod("CritChance", "BASE", 2, 0, 0, { type = "SkillPart", skillPart = 3 }),
		},
	},
	["sndr1-18"] = {
		[" Third Strike Double Crit Chance"] = {
			mod("CritChance", "MORE", 100, 0, 0, { type = "SkillPart", skillPart = 3 }),
		},
		["+50% Third Strike Critical Multiplier"] = {
			mod("CritMultiplier", "BASE", 50, 0, 0, { type = "SkillPart", skillPart = 3 }),
		},
		[" First And Second Strike Never Crit"] = {
			mod("NeverCrit", "FLAG", true, 0, 0, { type = "SkillPart", skillPartList = { 1, 2 } }),
		},
	},
	["sndr1-30"] = {
		["+15% Third Strike Damage"] = {
			mod("Damage", "MORE", 15, 0, 0, { type = "SkillPart", skillPart = 3 }),
			mod("SourceAilmentDamage", "MORE", 15, 0, 0, { type = "SkillPart", skillPart = 3 }),
		},
	},
	["sndr1-26"] = {
		["+25% Strike Two Damage"] = {
			mod("Damage", "MORE", 25, 0, 0, { type = "SkillPart", skillPart = 2 }),
			mod("SourceAilmentDamage", "MORE", 25, 0, 0, { type = "SkillPart", skillPart = 2 }),
		},
		["+25% Strike Two Area"] = {
			mod("AreaOfEffect", "INC", 25, 0, 0, { type = "SkillPart", skillPart = 2 }),
		},
	},
	["sndr1-7"] = {
		["+12% Third Strike Damage"] = {
			mod("Damage", "MORE", 12, 0, 0, { type = "SkillPart", skillPart = 3 }),
			mod("SourceAilmentDamage", "MORE", 12, 0, 0, { type = "SkillPart", skillPart = 3 }),
		},
		["5 Mana Gained"] = {
			mod("ManaOnHit", "BASE", 5, 0, 0, { type = "SkillPart", skillPart = 3 }),
		},
	},
	["sndr1-23"] = {
		[" Skips Third Strike"] = {
			mod("Condition:RiveSkipThirdStrike", "FLAG", true),
		},
	},
	["sndr1-21"] = {
		[" Change Sequence Of Strikes"] = {
			mod("Condition:RiveCadence", "FLAG", true),
		},
	},
	["sndr1-9"] = {
		["+50% First Strike Ignite Chance"] = {
			mod("ChanceToTriggerOnHit_Ailment_Ignite", "BASE", 50, ModFlag.Hit, 0, { type = "SkillPart", skillPart = 1 }),
		},
	},
	["sndr1-10"] = {
		["+50% Second Strike Ignite Chance"] = {
			mod("ChanceToTriggerOnHit_Ailment_Ignite", "BASE", 50, ModFlag.Hit, 0, { type = "SkillPart", skillPart = 2 }),
		},
	},
	["sndr1-31"] = {
		["+10% Bleed Duration On Third Strike"] = {
			mod("AilmentDuration_Ailment_Bleed", "INC", 10, 0, 0, { type = "SkillPart", skillPart = 3 }),
		},
	},
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
