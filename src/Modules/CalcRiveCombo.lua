-- Hit, bleed and ignite damage over one uninterrupted Rive cycle. Each strike's
-- calculations retain their own modifiers, critical chance and attack timing.
local calcs = ...

-- Evaluate an ailment with the actual applying strike instead of the globally
-- cached selection. CACHE skips circular debuff-stack lookups; skipCache keeps
-- this temporary environment out of the shared cache.
local function ailmentOutput(env, source, output, uuid, part, ailmentId)
	local chance = source.skillModList:Sum("BASE", source.skillCfg, "ChanceToTriggerOnHit_" .. ailmentId)
	if chance <= 0 then
		return
	end
	local ailmentEnv = calcs.initEnv(env.build, "CACHE", { skillPartOverrides = { [uuid] = part } })
	ailmentEnv.skipCache = true
	ailmentEnv.triggerSourceOverride = {
		skill = source,
		hitRate = (output.HitSpeed or output.Speed) * (output.HitChance or 100) / 100,
	}
	local group = { grantedEffect = env.data.skills[ailmentId], skillId = ailmentId,
		source = "Rive1", triggered = true, triggeredOnHit = true }
	local effect = { grantedEffect = group.grantedEffect, srcInstance = group }
	local ailment = calcs.createActiveSkill(effect, {}, ailmentEnv.player, group)
	ailmentEnv.player.mainSkill = ailment
	table.insert(ailmentEnv.player.activeSkillList, ailment)
	calcs.buildActiveSkillModList(ailmentEnv, ailment)
	calcs.perform(ailmentEnv, true)
	return ailmentEnv.player.output
end

function calcs.riveCombo(env)
	local skill = env.player.mainSkill
	if skill.activeEffect.grantedEffect.id ~= "Rive1" or isTriggered(skill) then
		return
	end
	local cfg = skill.skillCfg
	local cadence = env.player.modDB:GetCondition("RiveCadence", cfg)
	local skipThird = env.player.modDB:GetCondition("RiveSkipThirdStrike", cfg)
	local sequence = cadence and { 1, 2, 1, 2, 3 } or { 1, 2, 3 }
	if skipThird then
		table.remove(sequence)
	end
	local uuid = cacheSkillUUID(skill, env)
	local outputs = {}
	local ailments = {}
	local duration, damage = 0, 0
	local bleedDamage, igniteDamage = 0, 0
	local manaGained = 0
	for _, part in ipairs(sequence) do
		if not outputs[part] then
			-- CALCULATOR does not write to the shared skill-output cache. Override
			-- only this Rive group, leaving both saved part selectors untouched.
			local partEnv = calcs.initEnv(env.build, "CALCULATOR", {
				skillPartOverrides = { [uuid] = part },
			})
			local found
			for _, candidate in ipairs(partEnv.player.activeSkillList) do
				if cacheSkillUUID(candidate, partEnv) == uuid then
					partEnv.player.mainSkill = candidate
					found = candidate
					break
				end
			end
			if not found or found.skillFlags.disable then
				return
			end
			calcs.perform(partEnv, true)
			outputs[part] = partEnv.player.output
			ailments[part] = {
				bleed = ailmentOutput(env, found, outputs[part], uuid, part, "Ailment_Bleed"),
				ignite = ailmentOutput(env, found, outputs[part], uuid, part, "Ailment_Ignite"),
			}
		end
		local output = outputs[part]
		if not output.Speed or output.Speed <= 0 or not output.TotalDPS then
			return
		end
		local time = 1 / output.Speed
		duration = duration + time
		damage = damage + output.TotalDPS * time
		-- Single-target gain: one hit opportunity per strike, never per ailment tick.
		manaGained = manaGained + (output.ManaOnHit or 0) * (output.HitChance or 100) / 100
		bleedDamage = bleedDamage + (ailments[part].bleed and ailments[part].bleed.TotalDPS or 0) * time
		igniteDamage = igniteDamage + (ailments[part].ignite and ailments[part].ignite.TotalDPS or 0) * time
	end
	return {
		sequence = sequence,
		duration = duration,
		damage = damage,
		hitDPS = damage / duration,
		attackRate = #sequence / duration,
		strikes = outputs,
		ailments = ailments,
		bleedDPS = bleedDamage / duration,
		igniteDPS = igniteDamage / duration,
		manaOnHitRate = manaGained / duration,
	}
end
