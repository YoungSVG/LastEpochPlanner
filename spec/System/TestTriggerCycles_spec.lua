describe("Triggered skill cycles", function ()
	it("keeps ordinary triggers and stops mutually triggered spells from growing indefinitely", function ()
		newBuild()
		build.skillsTab:SelSkill(1, "Fireball")
		build.configTab.input.customMods = "100% Chance to cast Smite on Hit\n100% Chance to cast Fireball on Hit"
		build.configTab:BuildModList()
		for _ = 1, 3 do runCallback("OnFrame") end

		local foundSmite = false
		local count = 0
		for _, group in pairs(build.skillsTab.socketGroupList) do
			count = count + 1
			if group.skillId == "Smite" and group.source == "Fireball" then
				foundSmite = true
			end
			local seen = { [group.skillId] = true }
			for sourceId in string.gmatch(group.source or "", "[^/]+") do
				assert.are.equals(nil, seen[sourceId])
				seen[sourceId] = true
			end
		end
		assert.is_true(foundSmite)
		build.buildFlag = true
		runCallback("OnFrame")
		local nextCount = 0
		for _ in pairs(build.skillsTab.socketGroupList) do nextCount = nextCount + 1 end
		assert.are.equals(count, nextCount)
	end)
end)
