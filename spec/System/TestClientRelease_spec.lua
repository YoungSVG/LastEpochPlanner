describe("Staged client 1.5 data", function ()
	before_each(function ()
		newBuild()
	end)

	it("loads all client trees with the new skill owners", function ()
		local previous = treeVersions["1_5"]
		treeVersions["1_5"] = { display = "1.5", num = 1.5, url = "" }
		local ok, tree = pcall(new, "PassiveTree", "1_5")
		treeVersions["1_5"] = previous
		assert.is_true(ok)
		assert.are.equals("RadiantLance", tree.nodes["ra1an-32"].skillId)
		assert.are.equals("Dreamslash", tree.nodes["dr4sl-0"].skillId)
		assert.are.equals("PrimalistSummonElemental", tree.nodes["su3lem-0"].skillId)
		local count = 0
		for _ in pairs(tree.nodes) do count = count + 1 end
		assert.are.equals(4517, count)
	end)

	it("calculates the exported Radiant Lance spell with a shield", function ()
		build.itemsTab:CreateDisplayItemFromRaw("Rarity: NORMAL\nCavalier Shield")
		build.itemsTab:AddDisplayItem()
		build.skillsTab:SelSkill(1, "RadiantLance")
		runCallback("OnFrame")
		assert.are.equals(nil, build.calcsTab.mainEnv.player.mainSkill.disableReason)
		assert.is_true(build.calcsTab.mainOutput.TotalDPS > 0)
		assert.are.equals(24, build.calcsTab.mainOutput.ManaCost)
	end)

	it("calculates the exported Dreamslash attack with a permitted weapon", function ()
		build.itemsTab:CreateDisplayItemFromRaw("Rarity: NORMAL\nForestry Axe")
		build.itemsTab:AddDisplayItem()
		build.skillsTab:SelSkill(1, "Dreamslash")
		runCallback("OnFrame")
		assert.are.equals(nil, build.calcsTab.mainEnv.player.mainSkill.disableReason)
		assert.is_true(build.calcsTab.mainOutput.TotalDPS > 0)
		assert.are.equals(3, build.calcsTab.mainOutput.ManaCost)
	end)

	it("creates the Tide Elemental with its exported attacks", function ()
		build.skillsTab:SelSkill(1, "PrimalistSummonElemental")
		runCallback("OnFrame")
		local skill = build.calcsTab.mainEnv.player.mainSkill
		assert.is_true(skill.minion ~= nil)
		assert.is_true(skill.minion.output.TotalDPS > 0)
		assert.are.equals(15, build.calcsTab.mainOutput.ManaCost)
	end)
end)
