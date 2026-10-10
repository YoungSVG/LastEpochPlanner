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

	local function ailmentOutput(id, source)
		local env = build.calcsTab.mainEnv
		for _, skill in ipairs(env.player.activeSkillList) do
			if skill.activeEffect.grantedEffect.id == id and skill.socketGroup.source == (source or "Rive1") then
				return GlobalCache.cachedData.CACHE[cacheSkillUUID(skill, env)].Env.player.output
			end
		end
		return nil
	end

	it("applies ignite chance only on the specified strike and preserves chances above 100 percent", function ()
		newBuild()
		build.skillsTab:SelSkill(1, "Rive1")
		allocate("sndr1-9", 3)
		local first = selectPart(1)
		local ignite = ailmentOutput("Ailment_Ignite")
		assert.are.equals(150, ignite.TriggerChance)
		assert.are.equals(round(first.Speed * 1.5, 6), round(ignite.Speed, 6))
		selectPart(2)
		assert.are.equals(nil, ailmentOutput("Ailment_Ignite"))
		allocate("sndr1-10", 2)
		local second = selectPart(2)
		ignite = ailmentOutput("Ailment_Ignite")
		assert.are.equals(100, ignite.TriggerChance)
		assert.are.equals(second.Speed, ignite.Speed)
		selectPart(3)
		assert.are.equals(nil, ailmentOutput("Ailment_Ignite"))
	end)

	it("passes Massacre duration only to bleeding applied by the third strike", function ()
		newBuild()
		build.skillsTab:SelSkill(1, "Rive1")
		allocate("sndr1-31", 3)
		selectPart(1)
		local baseDuration = ailmentOutput("Ailment_Bleed").Duration
		assert.are.equals(75, ailmentOutput("Ailment_Bleed").TriggerChance)
		selectPart(2)
		assert.are.equals(baseDuration, ailmentOutput("Ailment_Bleed").Duration)
		selectPart(3)
		assert.are.equals(round(baseDuration * 1.3, 6), round(ailmentOutput("Ailment_Bleed").Duration, 6))
		allocate("sndr1-31", 1)
		selectPart(3)
		assert.are.equals(round(baseDuration * 1.1, 6), round(ailmentOutput("Ailment_Bleed").Duration, 6))
		build.configTab.input.customMods = "75% Chance to Bleed on Hit"
		build.configTab:BuildModList()
		build.skillsTab:SelSkill(1, "Fireball")
		selectPart(1)
		assert.are.equals(baseDuration, ailmentOutput("Ailment_Bleed", "Fireball").Duration)
		build.configTab.input.customMods = ""
		build.configTab:BuildModList()
		build.skillsTab:SelSkill(1, "Rive1")
		allocate("sndr1-31", 0)
		selectPart(3)
		assert.are.equals(nil, ailmentOutput("Ailment_Bleed"))
	end)

	it("inherits Brutality damage only for ailments applied by the third strike", function ()
		newBuild()
		build.skillsTab:SelSkill(1, "Rive1")
		build.configTab.input.customMods = "100% Chance to Bleed on Hit\n100% Chance to Ignite on Hit\n100% increased Damage"
		build.configTab:BuildModList()
		local baseline = {}
		for part = 1, 3 do
			selectPart(part)
			baseline[part] = { ailmentOutput("Ailment_Bleed").TotalDPS, ailmentOutput("Ailment_Ignite").TotalDPS }
		end
		allocate("sndr1-30", 3)
		for part = 1, 3 do
			selectPart(part)
			local multiplier = part == 3 and 1.45 or 1
			assert.are.equals(multiplier, round(ailmentOutput("Ailment_Bleed").TotalDPS / baseline[part][1], 2))
			assert.are.equals(multiplier, round(ailmentOutput("Ailment_Ignite").TotalDPS / baseline[part][2], 2))
		end
		allocate("sndr1-30", 1)
		selectPart(3)
		assert.are.equals(1.15, round(ailmentOutput("Ailment_Bleed").TotalDPS / baseline[3][1], 2))
		allocate("sndr1-30", 0)
		selectPart(3)
		assert.are.equals(baseline[3][1], ailmentOutput("Ailment_Bleed").TotalDPS)
		build.skillsTab:SelSkill(1, "Fireball")
		selectPart(1)
		local fireballBleed = ailmentOutput("Ailment_Bleed", "Fireball").TotalDPS
		allocate("sndr1-30", 3)
		selectPart(1)
		assert.are.equals(fireballBleed, ailmentOutput("Ailment_Bleed", "Fireball").TotalDPS)
	end)

	it("scales Iron Reach damage, ailments and area only on the second strike", function ()
		newBuild()
		build.skillsTab:SelSkill(1, "Rive1")
		build.configTab.input.customMods = "100% Chance to Bleed on Hit\n100% Chance to Ignite on Hit"
		build.configTab:BuildModList()
		local baseline = {}
		for part = 1, 3 do
			local output = selectPart(part)
			baseline[part] = { hit = output.TotalDPS, bleed = ailmentOutput("Ailment_Bleed").TotalDPS,
				ignite = ailmentOutput("Ailment_Ignite").TotalDPS }
		end
		local function check(points)
			allocate("sndr1-26", points)
			for part = 1, 3 do
				local output = selectPart(part)
				local multiplier = part == 2 and 1 + points * 0.25 or 1
				assert.are.equals(multiplier, round(output.TotalDPS / baseline[part].hit, 2))
				assert.are.equals(multiplier, round(ailmentOutput("Ailment_Bleed").TotalDPS / baseline[part].bleed, 2))
				assert.are.equals(multiplier, round(ailmentOutput("Ailment_Ignite").TotalDPS / baseline[part].ignite, 2))
				local skill = build.calcsTab.mainEnv.player.mainSkill
				assert.are.equals(part == 2 and points * 25 or 0, skill.skillModList:Sum("INC", skill.skillCfg, "AreaOfEffect"))
			end
		end
		check(4)
		check(1)
		check(0)
		build.skillsTab:SelSkill(1, "Fireball")
		local before = selectPart(1).TotalDPS
		allocate("sndr1-26", 4)
		assert.are.equals(before, selectPart(1).TotalDPS)
	end)

	it("applies Azure Crescendo damage and mana recovery only on the third strike", function ()
		newBuild()
		build.skillsTab:SelSkill(1, "Rive1")
		build.configTab.input.customMods = "100% Chance to Bleed on Hit"
		build.configTab:BuildModList()
		local baseline = {}
		for part = 1, 3 do
			local output = selectPart(part)
			baseline[part] = { hit = output.TotalDPS, bleed = ailmentOutput("Ailment_Bleed").TotalDPS, mana = output.Mana }
		end
		allocate("sndr1-7", 3)
		for part = 1, 3 do
			local output = selectPart(part)
			local multiplier = part == 3 and 1.36 or 1
			assert.are.equals(multiplier, round(output.TotalDPS / baseline[part].hit, 2))
			assert.are.equals(multiplier, round(ailmentOutput("Ailment_Bleed").TotalDPS / baseline[part].bleed, 2))
			assert.are.equals(baseline[part].mana, output.Mana)
			assert.are.equals(part == 3 and 15 or 0, output.ManaOnHit)
			assert.are.equals(round(15 / output.RiveComboDuration, 6), round(output.RiveComboManaOnHitRate, 6))
		end
		allocate("sndr1-21", 1)
		local cadence = selectPart(1)
		assert.are.equals(round(15 / cadence.RiveComboDuration, 6), round(cadence.RiveComboManaOnHitRate, 6))
		allocate("sndr1-23", 1)
		assert.are.equals(0, selectPart(1).RiveComboManaOnHitRate)
		allocate("sndr1-21", 0)
		assert.are.equals(0, selectPart(1).RiveComboManaOnHitRate)
		allocate("sndr1-23", 0)
		allocate("sndr1-7", 1)
		assert.are.equals(5, selectPart(3).ManaOnHit)
		allocate("sndr1-7", 0)
		assert.are.equals(0, selectPart(3).RiveComboManaOnHitRate)
		build.skillsTab:SelSkill(1, "Fireball")
		allocate("sndr1-7", 3)
		assert.are.equals(0, selectPart(1).ManaOnHit)
	end)

	it("restricts Triple Threat damage, area and stun increase to the third strike", function ()
		newBuild()
		build.skillsTab:SelSkill(1, "Rive1")
		build.configTab.input.customMods = "100% Chance to Bleed on Hit"
		build.configTab:BuildModList()
		local baseline = {}
		for part = 1, 3 do
			baseline[part] = selectPart(part).TotalDPS
		end
		selectPart(3)
		local bleed = ailmentOutput("Ailment_Bleed").TotalDPS
		allocate("sndr1-22", 1)
		for part = 1, 3 do
			local out = selectPart(part)
			assert.are.equals(part == 3 and 1.5 or 1, round(out.TotalDPS / baseline[part], 2))
			assert.are.equals(part == 3 and 50 or nil, out.StunChanceInc)
			local skill = build.calcsTab.mainEnv.player.mainSkill
			assert.are.equals(part == 3 and 50 or 0, skill.skillModList:Sum("INC", skill.skillCfg, "AreaOfEffect"))
		end
		assert.are.equals(1.5, round(ailmentOutput("Ailment_Bleed").TotalDPS / bleed, 2))
		assert.are.equals(nil, ailmentOutput("Ailment_Bleed").StunChanceInc)
		allocate("sndr1-22", 0)
		assert.are.equals(baseline[3], selectPart(3).TotalDPS)
		assert.are.equals(nil, build.calcsTab.mainOutput.StunChanceInc)
		build.skillsTab:SelSkill(1, "Fireball")
		local before = selectPart(1).TotalDPS
		allocate("sndr1-22", 1)
		assert.are.equals(before, selectPart(1).TotalDPS)
		assert.are.equals(nil, build.calcsTab.mainOutput.StunChanceInc)
	end)

	it("applies Coup de Grace only to the third strike and retains the highest kill threshold", function ()
		newBuild()
		build.skillsTab:SelSkill(1, "Rive1")
		local baseHit = selectPart(3).TotalDPS
		allocate("sndr1-32", 1)
		for part = 1, 3 do
			local output = selectPart(part)
			assert.are.equals(part == 3 and 15 or 0, output.CullPercent)
			assert.are.equals(15, output.RiveComboCullPercent)
		end
		assert.are.equals(baseHit, build.calcsTab.mainOutput.TotalDPS)
		build.configTab.modList:NewMod("CullPercent", "MAX", 10, "Test")
		assert.are.equals(15, selectPart(3).CullPercent)
		build.configTab.modList:NewMod("CullPercent", "MAX", 20, "Test")
		assert.are.equals(20, selectPart(3).CullPercent)
		build.configTab:BuildModList()
		allocate("sndr1-21", 1)
		assert.are.equals(15, selectPart(1).RiveComboCullPercent)
		allocate("sndr1-23", 1)
		assert.are.equals(0, selectPart(1).RiveComboCullPercent)
		allocate("sndr1-21", 0)
		assert.are.equals(0, selectPart(1).RiveComboCullPercent)
		allocate("sndr1-23", 0)
		allocate("sndr1-32", 0)
		assert.are.equals(0, selectPart(3).CullPercent)
		build.skillsTab:SelSkill(1, "Fireball")
		allocate("sndr1-32", 1)
		assert.are.equals(0, selectPart(1).CullPercent)
	end)

	it("applies Champion to every Rive strike and its ailments without duplicating global damage", function ()
		newBuild()
		build.skillsTab:SelSkill(1, "Rive1")
		build.configTab.input.customMods = "100% Chance to Bleed on Hit\n100% Chance to Ignite on Hit\n100% increased Damage"
		build.configTab:BuildModList()
		local baseline = {}
		for part = 1, 3 do
			local output = selectPart(part)
			baseline[part] = { hit = output.TotalDPS, bleed = ailmentOutput("Ailment_Bleed").TotalDPS,
				ignite = ailmentOutput("Ailment_Ignite").TotalDPS }
		end
		for _, points in ipairs({ 4, 1, 0 }) do
			allocate("sndr1-2", points)
			for part = 1, 3 do
				local output = selectPart(part)
				assert.are.equals(1 + points * 0.08, round(output.TotalDPS / baseline[part].hit, 2))
				assert.are.equals(1 + points * 0.08, round(ailmentOutput("Ailment_Bleed").TotalDPS / baseline[part].bleed, 2))
				assert.are.equals(1 + points * 0.08, round(ailmentOutput("Ailment_Ignite").TotalDPS / baseline[part].ignite, 2))
				assert.are.equals(points * 10, output.StunChanceInc or 0)
			end
		end
		allocate("sndr1-2", 4)
		allocate("sndr1-30", 3)
		local output = selectPart(3)
		assert.are.equals(1.91, round(output.TotalDPS / baseline[3].hit, 2))
		assert.are.equals(1.91, round(ailmentOutput("Ailment_Bleed").TotalDPS / baseline[3].bleed, 2))
		allocate("sndr1-22", 1)
		assert.are.equals(90, selectPart(3).StunChanceInc)
		assert.are.equals(40, selectPart(1).StunChanceInc)
		build.skillsTab:SelSkill(1, "Fireball")
		local other = selectPart(1).TotalDPS
		assert.are.equals(nil, build.calcsTab.mainOutput.StunChanceInc)
		allocate("sndr1-2", 0)
		assert.are.equals(other, selectPart(1).TotalDPS)
	end)

	it("weights bleed and ignite from each applying strike across the entire combo", function ()
		newBuild()
		build.skillsTab:SelSkill(1, "Rive1")
		allocate("sndr1-9", 3)
		allocate("sndr1-10", 2)
		allocate("sndr1-31", 3)
		allocate("sndr1-15", 4)
		allocate("sndr1-30", 3)
		allocate("sndr1-26", 4)
		local strikes = {}
		for part = 1, 3 do
			local out = selectPart(part)
			local ignite = ailmentOutput("Ailment_Ignite")
			strikes[part] = { time = 1 / out.Speed, bleed = ailmentOutput("Ailment_Bleed").TotalDPS,
				ignite = ignite and ignite.TotalDPS or 0 }
		end
		local function check(sequence)
			local time, bleed, ignite = 0, 0, 0
			for _, part in ipairs(sequence) do
				local strike = strikes[part]
				time = time + strike.time
				bleed = bleed + strike.bleed * strike.time
				ignite = ignite + strike.ignite * strike.time
			end
			local output = selectPart(3)
			assert.are.equals(round(bleed / time, 6), round(output.RiveComboBleedDPS, 6))
			assert.are.equals(round(ignite / time, 6), round(output.RiveComboIgniteDPS, 6))
			assert.are.equals(true, output.RiveComboIgniteDPS > 0)
			assert.are.equals(nil, ailmentOutput("Ailment_Ignite"))
			assert.are.equals(3, build.skillsTab.socketGroupList[1].skillPart)
		end
		check({ 1, 2, 3 })
		allocate("sndr1-21", 1)
		check({ 1, 2, 1, 2, 3 })
		allocate("sndr1-23", 1)
		check({ 1, 2, 1, 2 })
		allocate("sndr1-21", 0)
		check({ 1, 2 })
	end)

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

	it("weights combo hit damage by strike duration with Flurry and Focused Strike", function ()
		newBuild()
		build.skillsTab:SelSkill(1, "Rive1")
		build.configTab.input.customMods = "+40 Melee Physical Damage"
		build.configTab:BuildModList()
		allocate("sndr1-15", 4)
		allocate("sndr1-16", 3)
		allocate("sndr1-18", 1)
		allocate("sndr1-30", 3)
		local strikes = {}
		for part = 1, 3 do
			local output = selectPart(part)
			strikes[part] = { time = 1 / output.Speed, dps = output.TotalDPS }
		end
		local function check(sequence)
			local time, damage = 0, 0
			for _, part in ipairs(sequence) do
				time = time + strikes[part].time
				damage = damage + strikes[part].dps * strikes[part].time
			end
			local out = selectPart(3)
			assert.are.equals(round(damage / time, 6), round(out.RiveComboHitDPS, 6))
			assert.are.equals(round(#sequence / time, 6), round(out.RiveComboAttackRate, 6))
			assert.are.equals(round(time, 6), round(out.RiveComboDuration, 6))
			assert.are.equals(table.concat(sequence, ","), table.concat(build.calcsTab.mainEnv.riveCombo.sequence, ","))
		end
		check({ 1, 2, 3 })
		allocate("sndr1-21", 1)
		check({ 1, 2, 1, 2, 3 })
		allocate("sndr1-23", 1)
		check({ 1, 2, 1, 2 })
		allocate("sndr1-21", 0)
		check({ 1, 2 })
	end)

	it("keeps combo calculations independent of saved selections and cached strike outputs", function ()
		newBuild()
		build.skillsTab:SelSkill(1, "Rive1")
		local group = build.skillsTab.socketGroupList[1]
		group.skillPartCalcs = 2
		local first = selectPart(1)
		local comboDPS = first.RiveComboHitDPS
		local third = selectPart(3)
		assert.are.equals(comboDPS, third.RiveComboHitDPS)
		assert.are.equals(3, group.skillPart)
		assert.are.equals(2, group.skillPartCalcs)
		local env = build.calcsTab.mainEnv
		local cached = GlobalCache.cachedData.MAIN[cacheSkillUUID(env.player.mainSkill, env)]
		assert.are.equals(third.TotalDPS, cached.TotalDPS)
		assert.are.equals(3, cached.ActiveSkill.skillPart)
		build.skillsTab:SelSkill(1, "Fireball")
		assert.are.equals(nil, selectPart(1).RiveComboHitDPS)
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
