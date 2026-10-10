"""Extract native client sprites and pack them losslessly into planner atlases."""
import argparse
from collections import OrderedDict
import hashlib
import json
from pathlib import Path

from PIL import Image
import UnityPy

from export_client import soft_guid, write_json


class SpriteReader:
    def __init__(self, game, index):
        self.root = game / "Last Epoch_Data/StreamingAssets/LEAssetBundles"
        self.index = index
        self.cache = OrderedDict()
        permanent = self.bundle("PermaLoad.bundle")
        for asset in permanent.assets:
            for key in asset.container:
                self.index.setdefault(key, "PermaLoad.bundle")

    def bundle(self, name):
        if name not in self.cache:
            self.cache[name] = UnityPy.load(str(self.root / name))
        self.cache.move_to_end(name)
        while len(self.cache) > 24:
            # The permanent bundle contains most skill icons and is costly to reload.
            key = next(k for k in self.cache if k != "PermaLoad.bundle")
            del self.cache[key]
        return self.cache[name]

    def identity(self, record):
        soft = record["softRef"]
        if soft.get("p0") or soft.get("p1"):
            return self.index[f"{soft['p0']:016x}{soft['p1']:016x}"], soft["subPath"]
        if soft.get("guid", {}).get("_0") or soft.get("guid", {}).get("_1"):
            return self.index[soft_guid(soft)], soft["subPath"]
        pointer = record["sprite"]
        if not pointer["m_PathID"]:
            raise ValueError("Icon has no sprite reference")
        bundle = record["bundle"]
        if pointer["m_FileID"]:
            externals = next(v for k, v in record["externals"].items() if k != "CAB-monoscripts")
            external = externals[pointer["m_FileID"] - 1].split("/")[-1]
            bundle = external.removeprefix("CAB-") + ".bundle"
        return bundle, pointer["m_PathID"]

    def read(self, identity):
        bundle, target = identity
        for obj in self.bundle(bundle).objects:
            if obj.type.name != "Sprite":
                continue
            if isinstance(target, int):
                match = obj.path_id == target
            else:
                match = obj.peek_name() == target
            if match:
                image = obj.read().image
                if image.width == 0 or image.height == 0:
                    raise ValueError(f"Empty sprite {identity}")
                return image
        raise ValueError(f"Sprite not found: {identity}")


def build_icons(game, index_file, trees, output):
    index = json.loads(index_file.read_text(encoding="utf-8"))
    sources = json.loads((trees / "icon-sources.json").read_text(encoding="utf-8"))
    reader = SpriteReader(game, index)
    identities = {}
    node_icons = {}
    legacy = {}
    for node, source in sources.items():
        identity = reader.identity(source)
        raw_key = json.dumps(identity) + ":" + str(source["logicalSize"])
        key = "client_" + hashlib.sha256(raw_key.encode()).hexdigest()[:20]
        identities[key] = (identity, source["logicalSize"])
        node_icons[node] = key
        if source["oldIcon"]:
            legacy.setdefault(source["oldIcon"], set()).add(key)

    size, gap = 2048, 2
    sheet = Image.new("RGBA", (size, size))
    sheet_index = 0
    x = y = gap
    row_height = 0
    mapping = {}
    output.mkdir(parents=True, exist_ok=True)
    provenance = []

    def save_sheet():
        sheet.save(output / f"client-{sheet_index}.png", optimize=True)

    for count, (key, (identity, logical_size)) in enumerate(sorted(identities.items()), 1):
        image = reader.read(identity).convert("RGBA")
        if image.width + 2 * gap > size or image.height + 2 * gap > size:
            raise ValueError(f"Sprite exceeds atlas size: {identity}")
        if x + image.width + gap > size:
            x, y, row_height = gap, y + row_height + gap, 0
        if y + image.height + gap > size:
            save_sheet()
            sheet_index += 1
            sheet = Image.new("RGBA", (size, size))
            x = y = gap
            row_height = 0
        # Copy original pixels; no upscaling, sharpening or lossy re-encoding.
        sheet.paste(image, (x, y))
        mapping[key] = {"sheet": sheet_index, "width": logical_size, "height": logical_size,
                        "uv": [x / size, y / size, (x + image.width) / size, (y + image.height) / size]}
        provenance.append({"key": key, "bundle": identity[0], "sprite": identity[1],
                           "nativeWidth": image.width, "nativeHeight": image.height,
                           "sheet": sheet_index, "rect": [x, y, x + image.width, y + image.height],
                           "logicalSize": logical_size,
                           "pixelSHA256": hashlib.sha256(image.tobytes()).hexdigest()})
        x += image.width + gap
        row_height = max(row_height, image.height)
        if count % 100 == 0:
            print(f"Packed {count}/{len(identities)} native icons", flush=True)
    save_sheet()
    for old, keys in legacy.items():
        if len(keys) == 1:
            mapping[old] = mapping[next(iter(keys))]
    lines = ["-- Generated from native Last Epoch client sprites. Do not edit.", "return {"]
    for key, entry in sorted(mapping.items()):
        uv = ", ".join(str(value) for value in entry["uv"])
        lines.append(f'\t[{json.dumps(key)}] = {{ sheet = {entry["sheet"]}, width = {entry["width"]}, height = {entry["height"]}, {uv} }},')
    lines.append("}")
    (output / "ClientSprites.lua").write_text("\n".join(lines) + "\n", encoding="utf-8")
    write_json(output / "node-icons.json", node_icons)
    write_json(output / "provenance.json", provenance)
    verify_atlases(output, provenance)
    print(f"Packed {len(identities)} native icons in {sheet_index + 1} atlases", flush=True)


def verify_atlases(output, provenance):
    """Check every exported sprite against the original, decoded client pixels."""
    for index in sorted({record["sheet"] for record in provenance}):
        with Image.open(output / f"client-{index}.png") as atlas:
            for record in provenance:
                if record["sheet"] != index:
                    continue
                sprite = atlas.crop(record["rect"]).convert("RGBA")
                actual = hashlib.sha256(sprite.tobytes()).hexdigest()
                if actual != record["pixelSHA256"]:
                    raise ValueError(f"Atlas pixels changed for {record['key']}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game", type=Path, required=True)
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--trees", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.resolve().is_relative_to(args.game.resolve()):
        raise ValueError("Output must be outside the game installation")
    build_icons(args.game, args.index, args.trees, args.output)


if __name__ == "__main__":
    main()
