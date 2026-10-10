describe("Client skill equipment requirements", function ()
	local originalFireball
	before_each(function ()
		originalFireball = data.skills.Fireball
		data.skills.Fireball = copyTable(originalFireball, true)
		data.skills.Fireball.baseFlags = copyTable(originalFireball.baseFlags, true)
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
end)
