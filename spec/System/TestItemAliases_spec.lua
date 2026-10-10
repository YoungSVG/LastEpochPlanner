describe("Legacy item base names", function ()
	local originalAliases
	before_each(function ()
		originalAliases = data.itemBaseAliases
		-- A synthetic old name keeps this test valid when client names change again.
		data.itemBaseAliases = { ["Legacy Circlet"] = "Jewelled Circlet" }
	end)
	after_each(function ()
		data.itemBaseAliases = originalAliases
	end)

	it("recognizes an old normal item name and saves the current base name", function ()
		local item = new("Item", "Rarity: NORMAL\nLegacy Circlet\nImplicits: 0\n+12 Health")
		assert.are.equals("Jewelled Circlet", item.baseName)
		assert.are.equals(data.itemBases["Jewelled Circlet"], item.base)
		item:BuildAndParseRaw()
		assert.are.equals("Jewelled Circlet", item.baseName)
		assert.are.equals("+12 Health", item.explicitModLines[1].line)
	end)

	it("preserves magic prefixes and suffixes around the old base name", function ()
		local item = new("Item", "Rarity: MAGIC\nHealthy Legacy Circlet of Warding\nImplicits: 0\n+12 Health")
		assert.are.equals("Jewelled Circlet", item.baseName)
		assert.are.equals("Healthy ", item.namePrefix)
		assert.are.equals(" of Warding", item.nameSuffix)
		item:BuildAndParseRaw()
		assert.are.equals("Jewelled Circlet", item.baseName)
		assert.are.equals("+12 Health", item.explicitModLines[1].line)
	end)

	it("recognizes a separate old base line without changing a rare title", function ()
		local item = new("Item", "Rarity: RARE\nAncient Shelter\nLegacy Circlet\nImplicits: 0\n+12 Health")
		assert.are.equals("Jewelled Circlet", item.baseName)
		assert.are.equals("Ancient Shelter", item.title)
		item:BuildAndParseRaw()
		assert.are.equals("Jewelled Circlet", item.baseName)
		assert.are.equals("Ancient Shelter", item.title)
	end)

	it("recognizes a separate old unique base line", function ()
		local item = new("Item", "Rarity: UNIQUE\nCalamity\nLegacy Circlet\nImplicits: 0\n+12 Health")
		assert.are.equals("Jewelled Circlet", item.baseName)
		item:BuildAndParseRaw()
		assert.are.equals("Jewelled Circlet", item.baseName)
		assert.are.equals("Calamity", item.title)
	end)
end)
