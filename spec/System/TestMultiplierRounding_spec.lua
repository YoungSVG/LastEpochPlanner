describe("Damage multiplier rounding", function ()
	local function multiplier(class, values)
		local store = new(class)
		for _, value in ipairs(values) do
			store:AddMod({ name = "Damage", type = "MORE", value = value, flags = 0, keywordFlags = 0 })
		end
		return store:More(nil, "Damage")
	end

	for _, class in ipairs({ "ModDB", "ModList" }) do
		it("rounds half-percent ties independently of modifier order in " .. class, function ()
			-- Smite triggered by Hammer Throw inherits these three multipliers.
			-- Their exact product is 1.5 * 3.5 * 1.18 = 6.195.
			for _, values in ipairs({
				{ 50, 250, 18 }, { 50, 18, 250 }, { 250, 50, 18 },
				{ 250, 18, 50 }, { 18, 50, 250 }, { 18, 250, 50 },
			}) do
				assert.are.equals(6.2, multiplier(class, values))
			end
		end)

		it("preserves values on either side of the rounding boundary in " .. class, function ()
			assert.are.equals(6.19, multiplier(class, { 50, 250, 17.99999 }))
			assert.are.equals(6.2, multiplier(class, { 50, 250, 18.00001 }))
			assert.are.equals(0.83, multiplier(class, { -17 }))
		end)
	end
end)
