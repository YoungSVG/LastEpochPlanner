local applyRangeTests = {
	[{ "+(10-20) Health", 128, 1.0, "Integer" }] = "+15 Health",
	[{ "(5-14)% increased Health", 96, 0.38 }] = "3% increased Health",
	[{ "(5-14)% increased Health", 96, 0.38, "Thousandth" }] = "3.2% increased Health",
	[{ "+(2-6) to All Attributes", 48, 1.0, "Integer" }] = "+2 to All Attributes",
	[{ "+(7-8) Attunement", 38, 1.5, "Integer" }] = "+10 Attunement",
	[{ "7% increased Health", 0, 1.5, "Integer" }] = "10% increased Health",
}

describe("TestItemTools", function ()
	it("preserves descending unique rolls at both endpoints and in the middle", function ()
		assert.are.equals("54% less Mana", itemLib.applyRange("(54-48)% less Mana", 0))
		assert.are.equals("51% less Mana", itemLib.applyRange("(54-48)% less Mana", 128))
		assert.are.equals("48% less Mana", itemLib.applyRange("(54-48)% less Mana", 255))
	end)
	it("applies independent unique rolls to each range in one tooltip line", function ()
		local line = "Gain (15-21) Mana and (180-330) Ward"
		assert.are.equals("Gain 15 Mana and 330 Ward", itemLib.applyRange(line, { 0, 255 }))
		assert.are.equals("Gain 21 Mana and 180 Ward", itemLib.applyRange(line, { 255, 0 }))
	end)
	for args, expected in pairs(applyRangeTests) do
		it(string.format("tests applyRange('%s', %.2f, %.2f)", unpack(args)), function ()
			local result = itemLib.applyRange(unpack(args))
			assert.are.equals(expected, result)
		end)
	end
end)
