-- Direct-hit damage over one uninterrupted Rive cycle. Individual strike
-- calculations retain their own modifiers, critical chance and attack timing.
local calcs = ...

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
	local duration, damage = 0, 0
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
		end
		local output = outputs[part]
		if not output.Speed or output.Speed <= 0 or not output.TotalDPS then
			return
		end
		local time = 1 / output.Speed
		duration = duration + time
		damage = damage + output.TotalDPS * time
	end
	return {
		sequence = sequence,
		duration = duration,
		damage = damage,
		hitDPS = damage / duration,
		attackRate = #sequence / duration,
		strikes = outputs,
	}
end
