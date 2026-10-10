local defenceMath = dofile("src/Modules/DefenceMath.lua")
local function near(expected, actual)
	assert(math.abs(expected - actual) < 0.00001, tostring(actual) .. " differs from " .. expected)
end

-- Reference results for the ordinary-block curve recovered from client 1.5.2.2.
near(0, defenceMath.blockReduction(0, 100))
near(0, defenceMath.blockReduction(-100, 100))
near(37.54453175, defenceMath.blockReduction(100, 1))
near(12.35798382, defenceMath.blockReduction(100, 100))
near(35.58357438, defenceMath.blockReduction(1000, 100))
near(59.30500258, defenceMath.blockReduction(3000, 100))
near(68.54444543, defenceMath.blockReduction(3000, 50))

-- Increasing effectiveness helps, but ordinary block never fully negates a hit.
for _, level in ipairs({ 1, 50, 100 }) do
	local previous = 0
	for _, effectiveness in ipairs({ 1, 100, 1000, 10000, 100000, 1000000 }) do
		local reduction = defenceMath.blockReduction(effectiveness, level)
		assert(reduction > previous and reduction < 85)
		previous = reduction
	end
end
print("Standalone defence formula tests passed")
