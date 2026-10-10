describe("Client skill equipment requirements", function ()
	local originalFireball
	before_each(function ()
		originalFireball = data.skills.Fireball
		data.skills.Fireball = copyTable(originalFireball, true)
		data.skills.Fireball.baseFlags = copyTable(originalFireball.baseFlags, true)
		data.skills.Fireball.stats = copyTable(originalFireball.stats, true)
		newBuild()
	end)
	after_each(function ()
		data.skills.Fireball = originalFireball
	end)

	it("requires a shield without treating a spell as a shield attack", function ()
		data.skills.Fireball.baseFlags.requiresShield = true
		build.skillsTab:SelSkill(1, "Fireball")
		runCallback("OnFrame")
		assert.are.equals("This skill requires a Shield", build.calcsTab.mainEnv.player.mainSkill.disableReason)

		build.itemsTab:CreateDisplayItemFromRaw("Rarity: NORMAL\nCavalier Shield")
		build.itemsTab:AddDisplayItem()
		runCallback("OnFrame")
		local skill = build.calcsTab.mainEnv.player.mainSkill
		assert.are.equals(nil, skill.disableReason)
		assert.are.equals(nil, skill.skillFlags.shieldAttack)
		assert.is_true(build.calcsTab.mainOutput.TotalDPS > 0)
	end)

	it("rejects empty hands and weapons outside the permitted list", function ()
		data.skills.Fireball.weaponTypes = { ["Two-Handed Axe"] = true }
		build.skillsTab:SelSkill(1, "Fireball")
		runCallback("OnFrame")
		assert.is_true(build.calcsTab.mainEnv.player.mainSkill.skillFlags.disable)

		build.itemsTab:CreateDisplayItemFromRaw("Rarity: NORMAL\nBrass Sceptre")
		build.itemsTab:AddDisplayItem()
		runCallback("OnFrame")
		assert.is_true(build.calcsTab.mainEnv.player.mainSkill.skillFlags.disable)

		newBuild()
		build.skillsTab:SelSkill(1, "Fireball")
		build.itemsTab:CreateDisplayItemFromRaw("Rarity: NORMAL\nForestry Axe")
		build.itemsTab:AddDisplayItem()
		runCallback("OnFrame")
		assert.are.equals(nil, build.calcsTab.mainEnv.player.mainSkill.disableReason)
		assert.is_true(build.calcsTab.mainOutput.TotalDPS > 0)
	end)

	it("scales only the owning skill with fractional uncapped block chance", function ()
		data.skills.Fireball.stats["damage_+%_final_per_uncapped_block_chance"] = 1
		build.skillsTab:SelSkill(1, "Fireball")
		runCallback("OnFrame")
		local baseline = build.calcsTab.mainOutput.TotalDPS
		for _, block in ipairs({ 0, 75.25, 150.5 }) do
			build.configTab.input.customMods = "+" .. block .. "% Block Chance"
			build.configTab:BuildModList()
			runCallback("OnFrame")
			local expected = 1 + block / 100
			assert.are.equals(round(expected, 4), round(build.calcsTab.mainEnv.player.mainSkill.skillModList:More(nil, "Damage"), 4))
			-- Final damage rounds hit values, so compare DPS with a small tolerance.
			assert.is_true(math.abs(build.calcsTab.mainOutput.TotalDPS / baseline - expected) < 0.0002)
		end
		build.skillsTab:SelSkill(1, "LightningBlast")
		runCallback("OnFrame")
		local unrelatedDPS = build.calcsTab.mainOutput.TotalDPS
		build.configTab.input.customMods = ""
		build.configTab:BuildModList()
		runCallback("OnFrame")
		assert.are.equals(unrelatedDPS, build.calcsTab.mainOutput.TotalDPS)
	end)

	it("keeps continuous scaling separate from whole-step modifiers in both stores", function ()
		for _, class in ipairs({ "ModDB", "ModList" }) do
			local store = new(class)
			store.actor.output = { UncappedBlockChance = 75.25, Att = 24.9 }
			store:AddMod({ name = "Damage", type = "MORE", value = 1, flags = 0, keywordFlags = 0,
				{ type = "PerStat", stat = "UncappedBlockChance", continuous = true } })
			store:AddMod({ name = "Damage", type = "MORE", value = 10, flags = 0, keywordFlags = 0,
				{ type = "PerStat", stat = "Att", div = 10 } })
			assert.are.equals(round(1.7525 * 1.2, 6), round(store:More(nil, "Damage"), 6))
		end
	end)
end)
