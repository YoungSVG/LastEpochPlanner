local treeSprites = dofile("src/Modules/TreeSprites.lua")
local mapping = dofile("src/TreeData/ClientSprites.lua")
local created = 0
local function newImage()
	created = created + 1
	return {
		Load = function (self, path) self.path = path end,
		ImageSize = function () return 62, 62 end,
	}
end

local load = treeSprites.new({
	first = { sheet = 0, width = 42, height = 42, 0.1, 0.2, 0.3, 0.4 },
	second = { sheet = 0, width = 64, height = 64, 0.5, 0.6, 0.7, 0.8 },
}, newImage)
local first = load("first")
assert(first.width == 42 and first.height == 42, "Atlas dimensions must not enlarge nodes")
assert(first[1] == 0.1 and first[4] == 0.4, "Keep the sprite's atlas coordinates")
assert(first.handle.path == "TreeData/sprites/client-0.png")
assert(load("first") == first and created == 1, "Reuse an already loaded sprite")
local second = load("second")
assert(second.handle == first.handle and created == 1, "Share the atlas texture across nodes")
assert(second.width == 64, "Shared textures must retain each node's logical size")
local fallback = load("old-icon")
assert(fallback.handle.path == "TreeData/sprites/old-icon.png")
assert(fallback.width == 62 and fallback[1] == 0 and fallback[4] == 1)
assert(load("old-icon") == fallback and created == 2)

local count = 0
for key, sprite in pairs(mapping) do
	assert(sprite.width == 42 or sprite.width == 62 or sprite.width == 64, key)
	assert(sprite.width == sprite.height, key)
	assert(sprite[1] >= 0 and sprite[2] >= 0 and sprite[3] <= 1 and sprite[4] <= 1, key)
	assert(sprite[1] < sprite[3] and sprite[2] < sprite[4], key)
	local file = assert(io.open("src/TreeData/sprites/client-" .. sprite.sheet .. ".png", "rb"))
	assert(file:read(8) == "\137PNG\r\n\26\n")
	file:close()
	count = count + 1
end
assert(count > 1000, "Native sprite map is incomplete")
print("Standalone tree sprite tests passed")
