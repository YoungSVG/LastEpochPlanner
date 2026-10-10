-- Run from repository root: luajit spec/Standalone/Importers.lua
local offline = dofile("src/Modules/ImportOffline.lua")
local online = dofile("src/Modules/ImportLETools.lua")
local function sortedPairs(t)
	local keys = {}
	for key in pairs(t) do keys[#keys + 1] = key end
	table.sort(keys)
	local i = 0
	return function ()
		i = i + 1
		if keys[i] then return keys[i], t[keys[i]] end
	end
end
local context = {
	data = {
		itemBases = { Shield = { baseTypeID = 34, subTypeID = 112, implicits = { "+(10-20) Health" } } },
		uniques = { [7] = { name = "Test Unique", mods = { "+(5-10) Health" }, rollIds = { 0 } } },
		itemMods = { Item = { ["1_0"] = { type = "Prefix" }, ["2_0"] = { type = "Suffix" } } },
		LETools_itemBases = { shield = { baseTypeId = 34, subTypeId = 112 }, unique = { baseTypeId = 34, subTypeId = 112, uniqueId = 7 } },
		LETools_affixes = { prefix = 1, suffix = 2 },
	},
	tree = { classes = { [0] = { name = "Sentinel", ascendancies = { [1] = { name = "Paladin" } }, skills = { { treeId = "smite", name = "Smite" } } } } },
	hasRange = function (line) return line:find("%(%d+%-%d+%)") end,
	defaultAffixQuality = 128,
	sortedPairs = sortedPairs,
}
local function equal(actual, expected)
	assert(actual == expected, tostring(actual) .. " ~= " .. tostring(expected))
end
local function offlineItem(container)
	return { containerID = container, data = { 5, 92, 13, 34, 112, 0, 0, 255, 255, 255, 0, 0, 0 }, inventoryPosition = { x = 0, y = 0 } }
end
for container, slot in pairs({ [33] = "Blessing 1", [39] = "Blessing 7", [45] = "Blessing 10", [123] = "Idol Altar", [5] = "Weapon 2" }) do
	local item = offline.decodeItem(offlineItem(container), context)
	equal(item.slotName, slot)
	equal(item.baseName, "Shield")
	equal(item.implicitMods[1], "{range: 255}+(10-20) Health")
end
equal(offline.decodeItem(offlineItem(99), context), nil)
equal(offline.decodeItem(offlineItem(29), context).slotName, "Idol 1,1")
local item = offlineItem(5)
item.data[12] = 194 -- two affixes, one sealed and one corrupted
item.data[13], item.data[14], item.data[15] = 0, 1, 50
item.data[16], item.data[17], item.data[18] = 0, 2, 200
local decoded = offline.decodeItem(item, context)
equal(#decoded.affixes, 2)
equal(decoded.affixes[1].sealed, true)
equal(decoded.affixes[2].corrupted, true)
equal(decoded.affixes[2].range, 200)
local save = {
	characterClass = 0, characterName = "Offline", level = 50, chosenMastery = 1, cycle = 7,
	savedCharacterTree = { nodeIDs = { 2 }, nodePoints = { 3 } },
	savedSkillTrees = { { treeID = "smite", nodeIDs = { 4 }, nodePoints = { 2 } } },
	savedItems = { item },
}
local character = offline.decodeCharacter(save, context)
equal(character.name, "Offline")
equal(character.ascendancyName, "Paladin")
equal(character.abilities[1], "Smite")
equal(character.hashes[1], "Sentinel-2#3")
equal(character.hashes[3], "smite-4#2")
local remote = {
	bio = { characterClass = 0, chosenMastery = 1, level = 50 },
	charTree = { selected = { [2] = 3 } },
	skillTrees = { { treeID = "smite", selected = { [4] = 2 } } },
	equipment = { weapon2 = { id = "shield", affixes = { { id = "prefix", tier = 1, r = 0 } }, sealedAffix = { id = "suffix", tier = 1, r = 200 } } },
	idols = {}, blessings = {},
}
character = online.decodeCharacter(remote, context)
equal(character.class, "Sentinel")
equal(character.abilities[1], "Smite")
equal(character.items[1].slotName, "Weapon 2")
equal(character.items[1].affixes[1].range, 0)
equal(character.items[1].affixes[2].sealed, true)
remote.equipment.weapon2 = { id = "unique", affixes = {}, ur = { 42 } }
equal(online.decodeCharacter(remote, context).items[1].rarity, "UNIQUE")
remote.equipment.weapon2.corruptedAffix = { id = "prefix", tier = 1 }
character = online.decodeCharacter(remote, context)
equal(character.items[1].rarity, "LEGENDARY")
equal(character.items[1].affixes[1].corrupted, true)
equal(character.items[1].affixes[1].range, 128)
equal(character.items[1].explicitMods[1], "{unique}{range: 42}+(5-10) Health")
equal(_G.processItemData, nil)
equal(_G.proccessItemAffix, nil)
equal(_G.data, nil)
equal(_G.main, nil)
print("PASS: standalone offline and LETools importers (no application globals)")
