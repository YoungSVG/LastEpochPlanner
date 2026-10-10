-- Last Epoch Planner
-- LETools data decoder. No UI or application globals.
local importer = {}

function importer.decodeCharacter(saveContent, context)
	local data = context.data
	local tree = context.tree
	local hasRange = context.hasRange
	local defaultAffixQuality = context.defaultAffixQuality
	local pairsSortByKey = context.sortedPairs
	local classId = saveContent.bio.characterClass
	local className = tree.classes[classId].name
	local char = {
		["league"] = "Cycle",
		["name"] = "LETools import",
		["level"] = saveContent.bio.level,
		["class"] = className,
		["ascendancy"] = saveContent.bio.chosenMastery,
		["classId"] = classId,
		["abilities"] = {},
		["items"] = {},
		["hashes"] = {}
	}
	for passive, nbPoints in pairs(saveContent["charTree"]["selected"]) do
		table.insert(char["hashes"], className .. "-" .. passive .. "#" .. nbPoints)
	end
	for _, skillTree in pairs(saveContent["skillTrees"]) do
		table.insert(char["hashes"], skillTree['treeID'] .. "-" .. 0 .. "#1")
		local skillList = tree.classes[classId].skills
		for _, skill in ipairs(skillList) do
			if skill.treeId == skillTree['treeID'] then
				table.insert(char["abilities"], skill.name)
			end
		end
		for skill, nbPoints in pairs(skillTree["selected"]) do
			if nbPoints > 0 then
				table.insert(char["hashes"], skillTree['treeID'] .. "-" .. skill .. "#" .. nbPoints)
			end
		end
	end
	local onlineImportSlotMap = {
		["weapon1"] = "Weapon 1",
		["weapon2"] = "Weapon 2",
		["head"] = "Helmet",
		["chest"] = "Body Armor",
		["hands"] = "Gloves",
		["feet"] = "Boots",
		["amulet"] = "Amulet",
		["ring1"] = "Ring 1",
		["ring2"] = "Ring 2",
		["waist"] = "Belt",
		["relic"] = "Relic",
		["idol_altar"] = "Idol Altar",
	}

	for i = 1, 10 do
		onlineImportSlotMap["Blessing " .. i] = "Blessing " .. i
	end

	local function processItemAffix(affixData, attribute)
		local affixId = data.LETools_affixes[affixData.id]
		if affixId then
			local affixTier = affixData.tier - 1
			local modId = affixId .. "_" .. affixTier
			local modData = data.itemMods.Item[modId]
			local range = (affixData.r or defaultAffixQuality)
			local itemAffix = { ["range"] = range, ["modId"] = modId }

			if attribute == "sealed" then
				itemAffix.sealed = true
			elseif attribute == "corrupted" then
				itemAffix.corrupted = true
			elseif modData.type == "Prefix" then
				itemAffix.prefix = true
			else
				itemAffix.suffix = true
			end
			return itemAffix
		end
	end

	local function processItemData(slotName, itemData)
		local item = { ["slotName"] = onlineImportSlotMap[slotName] }
		local baseTypeID = data.LETools_itemBases[itemData.id].baseTypeId
		local subTypeID = data.LETools_itemBases[itemData.id].subTypeId
		local uniqueId = data.LETools_itemBases[itemData.id].uniqueId

		for itemBaseName, itemBase in pairs(data.itemBases) do
			if itemBase.baseTypeID == baseTypeID and itemBase.subTypeID == subTypeID then
				item.base = itemBase
				item.name = itemBaseName
				item.baseName = itemBaseName
				if slotName == "idol" then
					item["rarityType"] = "IDOL"
					item["rarity"] = "IDOL"
					local posX = itemData["x"]
					local posY = 6 - itemData["y"] - (itemBase.height - 1)
					item["slotName"] = "Idol " .. posX .. "," .. posY
				end
			end
		end

		item["rarity"] = item["rarity"] or "RARE"
		item["rarityType"] = item["rarityType"] or "BASIC"
		item["explicitMods"] = {}
		item["affixes"] = {}

		for _, affixData in ipairs(itemData["affixes"] or {}) do
			table.insert(item.affixes, processItemAffix(affixData))
		end
		if itemData.sealedAffix then
			table.insert(item.affixes, processItemAffix(itemData.sealedAffix, "sealed"))
		end

		if itemData.corruptedAffix then
			table.insert(item.affixes, processItemAffix(itemData.corruptedAffix, "corrupted"))
		end

		if uniqueId then
			local uniqueBase = data.uniques[uniqueId]
			if uniqueBase then
				item.name = uniqueBase.name
				item["rarityType"] = item["rarityType"] or "UNIQUE"
				-- Unique with crafted affixes becomes Legendary
				if #item.affixes > 0 then
					item["rarity"] = "LEGENDARY"
				else
					item["rarity"] = "UNIQUE"
				end
				for i, modLine in ipairs(uniqueBase.mods) do
					if hasRange(modLine) and type(uniqueBase.rollIds[i]) == "table" then
						local ranges = {}
						for n, id in ipairs(uniqueBase.rollIds[i]) do
							ranges[n] = itemData.ur and itemData.ur[id + 1] or defaultAffixQuality
						end
						table.insert(item.explicitMods, "{unique}" .. context.applyRange(modLine, ranges))
					elseif hasRange(modLine) then
						local range = defaultAffixQuality
						if itemData['ur'] and #itemData['ur'] > 0 then
							range = itemData["ur"][uniqueBase.rollIds[i] + 1]
						end
						table.insert(item.explicitMods, "{unique}{range: " .. range .. "}" .. modLine)
					else
						table.insert(item.explicitMods, "{unique}" .. modLine)
					end
				end
			end
		end

		if item.base then
			item.implicitMods = {}
			for i, implicit in ipairs(item.base.implicits) do
				local range = defaultAffixQuality
				if itemData['ir'] then
					range = itemData["ir"][i]
				end
				table.insert(item.implicitMods, "{range: " .. range .. "}" .. implicit)
			end
			return item
		end
	end

	for slotName, itemData in pairsSortByKey(saveContent["equipment"]) do
		local item = processItemData(slotName, itemData)
		if item then
			table.insert(char["items"], item)
		end
	end
	for _, itemData in pairs(saveContent["idols"]) do
		local item = processItemData("idol", itemData)
		if item then
			table.insert(char["items"], item)
		end
	end
	for i = 1, 10 do
		local blessingData = saveContent["blessings"][i]
		if blessingData then
			local item = processItemData("Blessing " .. i, blessingData)
			if item then
				table.insert(char["items"], item)
			end
		end
	end
	return char
end

return importer
