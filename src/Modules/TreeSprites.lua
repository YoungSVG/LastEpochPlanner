-- Load native-resolution atlas artwork without changing node layout dimensions.
local treeSprites = {}

function treeSprites.new(mapping, newImage)
	local sheets = {}
	local sprites = {}
	return function(icon)
		if sprites[icon] then
			return sprites[icon]
		end
		local entry = mapping[icon]
		local sprite
		if entry then
			local handle = sheets[entry.sheet]
			if not handle then
				handle = newImage()
				handle:Load("TreeData/sprites/client-" .. entry.sheet .. ".png")
				sheets[entry.sheet] = handle
			end
			sprite = {
				handle = handle, width = entry.width, height = entry.height,
				entry[1], entry[2], entry[3], entry[4],
			}
		else
			local handle = newImage()
			handle:Load("TreeData/sprites/" .. icon .. ".png")
			local width, height = handle:ImageSize()
			sprite = { handle = handle, width = width, height = height, 0, 0, 1, 1 }
		end
		sprites[icon] = sprite
		return sprite
	end
end

return treeSprites
