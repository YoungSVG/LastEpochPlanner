-- Last Epoch Planner
-- Offline save decoder. Input JSON is decoded by the caller.
local importer = {}

local offlineImportSlotMap = {
	[4] = "Weapon 1",
	[5] = "Weapon 2",
	[2] = "Helmet",
	[3] = "Body Armor",
	[6] = "Gloves",
	[8] = "Boots",
	[11] = "Amulet",
	[9] = "Ring 1",
	[10] = "Ring 2",
	[7] = "Belt",
	[12] = "Relic",
	[123] = "Idol Altar"
}

for i = 1, 7 do
	offlineImportSlotMap[32 + i] = "Blessing " .. i
end
for i = 1, 3 do
	offlineImportSlotMap[42 + i] = "Blessing " .. (7 + i)
end

function importer.decodeItem(itemData, context)
	local data = context.data
	local hasRange = context.hasRange
	if itemData["containerID"] <= 12 or itemData["containerID"] == 29 or
		itemData["containerID"] >= 33 and itemData["containerID"] <= 39 or
		itemData["containerID"] >= 43 and itemData["containerID"] <= 45 or
		itemData["containerID"] == 123 then
		local item = {}
		local baseTypeID = itemData["data"][4]
		local subTypeID = itemData["data"][5]
		if itemData["containerID"] == 29 then
			local posX = itemData["inventoryPosition"]["x"] + 1
			local posY = itemData["inventoryPosition"]["y"] + 1
			item["slotName"] = "Idol " .. posX .. "," .. posY
			item["rarityType"] = "IDOL"
			item["rarity"] = "IDOL"
		else
			item["slotName"] = offlineImportSlotMap[itemData["containerID"]]
		end

		for itemBaseName, itemBase in pairs(data.itemBases) do
			if itemBase.baseTypeID == baseTypeID and itemBase.subTypeID == subTypeID then
				item.baseName = itemBaseName
				item.base = itemBase
				item.implicitMods = {}
				for i, implicit in ipairs(itemBase.implicits) do
					local range = itemData["data"][7 + i]
					table.insert(item.implicitMods, "{range: " .. range .. "}" .. implicit)
				end
				local rarity = itemData["data"][6]
				item["explicitMods"] = {}
				item["affixes"] = {}
				local nbAffixesIndex = 12
				if rarity >= 7 and rarity <= 9 then
					item["rarity"] = "UNIQUE"
					item["rarityType"] = item["rarityType"] or "UNIQUE"
					local uniqueIDIndex = 8 + 3 -- 3 is the maximum amount of implicits
					local uniqueID = itemData["data"][uniqueIDIndex] * 256 + itemData["data"][uniqueIDIndex + 1]
					local uniqueBase = data.uniques[uniqueID]
					item["name"] = uniqueBase.name
					for i, modLine in ipairs(uniqueBase.mods) do
						if hasRange(modLine) then
							local rollId = uniqueBase.rollIds[i]
							local range = itemData["data"][uniqueIDIndex + 2 + rollId]
							table.insert(item.explicitMods, "{unique}{range: " .. range .. "}" .. modLine)
						else
							table.insert(item.explicitMods, "{unique}" .. modLine)
						end
					end
					if rarity == 9 then
						item["rarity"] = "LEGENDARY"
					end
					nbAffixesIndex = uniqueIDIndex + 2 + 8 -- 8 is the maximum amount of unique mods
				else
					item["name"] = itemBaseName
					item["rarity"] = item["rarity"] or "RARE"
					item["rarityType"] = item["rarityType"] or "BASIC"
				end
				if itemData["data"][nbAffixesIndex] then
					local nbMods = itemData["data"][nbAffixesIndex] % 8
					local nbSealedAffix = math.floor(itemData["data"][nbAffixesIndex] / 64) % 2
					local nbCorruptedAffix = math.floor(itemData["data"][nbAffixesIndex] / 128) % 2
					for i = 0, nbMods - 1 do
						local dataId = nbAffixesIndex + 1 + 3 * i
						if itemData["data"][dataId] ~= nil and itemData["data"][dataId + 1] ~= nil then
							local affixId = itemData["data"][dataId + 1] + (itemData["data"][dataId] % 16) * 256
							local affixTier = math.floor(itemData["data"][dataId] / 16)
							local modId = affixId .. "_" .. affixTier
							local modData = data.itemMods.Item[modId]
							local range = itemData["data"][dataId + 2]
							local affix = { ["range"] = range, ["modId"] = modId }

							if modData then
								if nbSealedAffix == 1 then
									affix.sealed = true
									nbSealedAffix = 0
								elseif nbCorruptedAffix == 1 then
									affix.corrupted = true
									nbCorruptedAffix = 0
								elseif modData.type == "Prefix" then
									affix.prefix = true
								else
									affix.suffix = true
								end
								table.insert(item.affixes, affix)
							end
						end
					end
				end
				return item
			end
		end
	end
end

function importer.decodeCharacter(saveContent, context)
	local tree = context.tree
	local pairsSortByKey = context.sortedPairs
	local classId = saveContent["characterClass"]
	local className = tree.classes[classId].name
	local char = {
		["name"] = saveContent["characterName"],
		["level"] = saveContent["level"],
		["class"] = className,
		["ascendancy"] = saveContent['chosenMastery'],
		["ascendancyName"] = tree.classes[classId].ascendancies[saveContent['chosenMastery']].name,
		["classId"] = classId,
		["abilities"] = {},
		["items"] = {},
		["hashes"] = {}
	}
	char.league = saveContent["cycle"] == 7 and "Cycle" or "Legacy"
	for passiveIdx, passive in pairs(saveContent["savedCharacterTree"]["nodeIDs"]) do
		local nbPoints = saveContent["savedCharacterTree"]["nodePoints"][passiveIdx]
		table.insert(char["hashes"], className .. "-" .. passive .. "#" .. nbPoints)
	end
	for _, skillTree in pairs(saveContent["savedSkillTrees"]) do
		local skillName
		local treeId = skillTree['treeID']

		local skillList = tree.classes[classId].skills
		for _, skill in ipairs(skillList) do
			if skill.treeId == treeId then
				skillName = skill.name
			end
		end

		if skillName then
			table.insert(char["hashes"], treeId .. "-" .. 0 .. "#1")
			table.insert(char["abilities"], skillName)
			for skillIdx, skill in pairs(skillTree["nodeIDs"]) do
				local nbPoints = skillTree["nodePoints"][skillIdx]
				table.insert(char["hashes"], treeId .. "-" .. skill .. "#" .. nbPoints)
			end
		end
	end
	for _, itemData in pairsSortByKey(saveContent["savedItems"]) do
		local item = importer.decodeItem(itemData, context)
		if item then
			table.insert(char["items"], item)
		end
	end

	return char
end


return importer
