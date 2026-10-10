-- Pure defence formulas. Percentages returned on the 0..100 scale.
local defenceMath = {}

-- Ordinary block mitigation from the Last Epoch 1.5.2.2 client.
-- See docs/client-formulas.md for provenance and supported scope.
function defenceMath.blockReduction(effectiveness, enemyLevel)
	if effectiveness <= 0 then
		return 0
	end
	local level = enemyLevel + 5
	local scaledEffectiveness = 0.0006 * effectiveness ^ 2 + 1.2 * effectiveness
	return 100 * (0.6 * scaledEffectiveness / (scaledEffectiveness + 60 * level)
		+ 0.25 * (3 * effectiveness) / (3 * effectiveness + 0.03 * level ^ 2 + 40))
end

return defenceMath
