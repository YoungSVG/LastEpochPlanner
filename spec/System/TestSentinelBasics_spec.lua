describe("Sentinel client ability basics", function ()
	it("calculates the native mana costs for unmodified void spells", function ()
		for skillId, cost in pairs({ AbyssalEchoes = 35, DevouringOrb = 18, Anomaly = 0 }) do
			newBuild()
			build.skillsTab:SelSkill(1, skillId)
			runCallback("OnFrame")
			assert.are.equals(cost, build.calcsTab.mainOutput.ManaCost)
		end
	end)

	it("requires a two-handed sword or axe for Void Cleave", function ()
		for _, weaponType in ipairs({ "None", "One-Handed Sword", "Two-Handed Mace", "Two-Handed Axe", "Two-Handed Sword" }) do
			newBuild()
			build.skillsTab:SelSkill(1, "VoidCleave")
			if weaponType ~= "None" then
				local baseName
				for name, base in pairsSortByKey(data.itemBases) do
					if base.type == weaponType then
						baseName = name
						break
					end
				end
				assert.is_not_nil(baseName)
				build.itemsTab:CreateDisplayItemFromRaw("Rarity: NORMAL\n" .. baseName)
				build.itemsTab:AddDisplayItem()
			end
			runCallback("OnFrame")
			local skill = build.calcsTab.mainEnv.player.mainSkill
			if weaponType == "Two-Handed Axe" or weaponType == "Two-Handed Sword" then
				assert.is_nil(skill.disableReason)
				assert.are.equals(15, build.calcsTab.mainOutput.ManaCost)
				assert.is_true(build.calcsTab.mainOutput.TotalDPS > 0)
			else
				assert.is_true(skill.skillFlags.disable)
			end
		end
	end)
end)
