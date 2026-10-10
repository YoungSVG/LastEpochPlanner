describe("Rive strike calculations", function ()
	local function selectPart(part)
		build.skillsTab.socketGroupList[1].skillPart = part
		build.buildFlag = true
		runCallback("OnFrame")
		return build.calcsTab.mainOutput
	end

	local function allocate(id, points)
		local node = build.spec.nodes[id]
		node.alloc = points
		build.spec.tree:ProcessStats(node)
		assert.are.equals(nil, node.unknown)
		assert.are.equals(nil, node.extra)
		build.spec.allocNodes[id] = points > 0 and node or nil
	end

	it("applies Flurry speed only to the first two strikes and scales with allocated points", function ()
		newBuild()
		build.skillsTab:SelSkill(1, "Rive1")
		local firstSpeed = selectPart(1).Speed
		local thirdSpeed = selectPart(3).Speed
		allocate("sndr1-15", 4)
		assert.are.equals(1.4, round(selectPart(1).Speed / firstSpeed, 5))
		assert.are.equals(1.4, round(selectPart(2).Speed / firstSpeed, 5))
		assert.are.equals(thirdSpeed, selectPart(3).Speed)
		allocate("sndr1-15", 1)
		assert.are.equals(1.1, round(selectPart(1).Speed / firstSpeed, 5))
		allocate("sndr1-15", 0)
		assert.are.equals(firstSpeed, selectPart(1).Speed)
	end)

	it("combines Concentration and Focused Strike without allowing the first two strikes to crit", function ()
		newBuild()
		build.skillsTab:SelSkill(1, "Rive1")
		local baseCrit = selectPart(1).CritChance
		local baseMulti = selectPart(3).CritMultiplier
		allocate("sndr1-16", 3)
		assert.are.equals(baseCrit + 3, selectPart(1).CritChance)
		assert.are.equals(baseCrit + 3, selectPart(2).CritChance)
		assert.are.equals(baseCrit + 6, selectPart(3).CritChance)
		allocate("sndr1-18", 1)
		assert.are.equals(0, selectPart(1).CritChance)
		assert.are.equals(0, selectPart(2).CritChance)
		assert.are.equals((baseCrit + 6) * 2, selectPart(3).CritChance)
		assert.are.equals(baseMulti + 0.5, selectPart(3).CritMultiplier)
		allocate("sndr1-18", 0)
		assert.are.equals(baseCrit + 3, selectPart(1).CritChance)
	end)

	it("applies Brutality as a third-strike multiplier without affecting another skill", function ()
		newBuild()
		build.skillsTab:SelSkill(1, "Rive1")
		local firstDPS = selectPart(1).TotalDPS
		local thirdDPS = selectPart(3).TotalDPS
		allocate("sndr1-30", 3)
		assert.are.equals(firstDPS, selectPart(1).TotalDPS)
		assert.are.equals(firstDPS, selectPart(2).TotalDPS)
		-- Final damage rounds intermediate values; inspect the multiplier exactly.
		local ratio = selectPart(3).TotalDPS / thirdDPS
		assert.are.equals(true, math.abs(ratio - 1.45) < 0.01)
		local skill = build.calcsTab.mainEnv.player.mainSkill
		assert.are.equals(1.45, skill.skillModList:More(skill.skillCfg, "Damage"))
		allocate("sndr1-15", 4)
		allocate("sndr1-16", 3)
		allocate("sndr1-18", 1)
		build.skillsTab:SelSkill(1, "Fireball")
		local otherDPS = selectPart(1).TotalDPS
		for _, id in ipairs({ "sndr1-15", "sndr1-16", "sndr1-18", "sndr1-30" }) do
			allocate(id, 0)
		end
		assert.are.equals(otherDPS, selectPart(1).TotalDPS)
	end)

	it("disables only the skipped third strike and restores it when Double Slash is refunded", function ()
		newBuild()
		build.skillsTab:SelSkill(1, "Rive1")
		local firstDPS = selectPart(1).TotalDPS
		local thirdDPS = selectPart(3).TotalDPS
		allocate("sndr1-23", 1)
		selectPart(3)
		local skill = build.calcsTab.mainEnv.player.mainSkill
		assert.are.equals(true, skill.skillFlags.disable)
		assert.are.equals(true, skill.skillFlags.multiPart)
		assert.are.equals("Double Slash skips Rive's third strike", skill.disableReason)
		assert.are.equals(0, build.calcsTab.mainOutput.TotalDPS or 0)
		assert.are.equals(firstDPS, selectPart(1).TotalDPS)
		assert.are.equals(firstDPS, selectPart(2).TotalDPS)
		allocate("sndr1-23", 0)
		assert.are.equals(thirdDPS, selectPart(3).TotalDPS)
	end)

	it("uses native damage effectiveness and timing for each strike without leaking overrides", function ()
		newBuild()
		build.skillsTab:SelSkill(1, "Rive1")
		build.configTab.input.customMods = "+40 Melee Physical Damage"
		build.configTab:BuildModList()
		local first = selectPart(1)
		local firstDPS, firstSpeed = first.TotalDPS, first.Speed
		assert.are.equals(52, first.PhysicalDamageBase)
		assert.are.equals(firstDPS, selectPart(2).TotalDPS)
		local third = selectPart(3)
		assert.are.equals(102, third.PhysicalDamageBase)
		assert.are.equals(round(0.6 / 0.7, 5), round(third.Speed / firstSpeed, 5))
		assert.are.equals("Third strike", build.calcsTab.mainEnv.player.mainSkill.skillPartName)
		assert.are.equals(1.25, data.skills.Rive1.stats.damageEffectiveness)
		assert.are.equals(firstDPS, selectPart(1).TotalDPS)
		assert.are.equals(firstDPS, selectPart(0).TotalDPS)
		assert.are.equals(3, #build.controls.mainSkillPart.list)
	end)

	it("persists independent main and calculation-tab strike selections", function ()
		newBuild()
		build.skillsTab:SelSkill(1, "Rive1")
		local group = build.skillsTab.socketGroupList[1]
		group.skillPart, group.skillPartCalcs = 3, 2
		local xml = {}
		build.skillsTab:Save(xml)
		newBuild()
		build.skillsTab:Load(xml, "Rive parts test")
		group = build.skillsTab.socketGroupList[1]
		assert.are.equals(3, group.skillPart)
		assert.are.equals(2, group.skillPartCalcs)
		build.buildFlag = true
		runCallback("OnFrame")
		assert.are.equals("Third strike", build.calcsTab.mainEnv.player.mainSkill.skillPartName)
	end)
end)
