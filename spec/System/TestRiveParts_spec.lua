describe("Rive strike calculations", function ()
	local function selectPart(part)
		build.skillsTab.socketGroupList[1].skillPart = part
		build.buildFlag = true
		runCallback("OnFrame")
		return build.calcsTab.mainOutput
	end

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
