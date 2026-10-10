# Exporting data and icons from the client

The Python tools in `helperScripts` read an installed Last Epoch client. They do
not modify the installation or read character saves. Run them from the repository
root and keep intermediate files outside both the repository and the game folder.

The checked icon set comes from client **1.5.2.2**, Steam build **25816319**, Unity
**6000.4.8f1**. Source file fingerprints and individual sprite pixel hashes are in
`docs/client-icons-1.5.2.2.json`. Game artwork belongs to Eleventh Hour Games.

## Requirements

Install the pinned Python dependencies:

```powershell
python -m pip install -r helperScripts/client-requirements.txt
```

This client uses IL2CPP metadata version 39. Generate dummy assemblies with
[Cpp2IL 2022.1.0-pre-release.21](https://github.com/SamboyCoding/Cpp2IL/releases/tag/2022.1.0-pre-release.21):

```powershell
Cpp2IL.exe --game-path "D:\Steam\steamapps\common\Last Epoch" --exe-name "Last Epoch" --use-processor attributeanalyzer --output-as dummydll --output-to ..\client-assemblies
```

The `attributeanalyzer` processor is required: without serialized-field
attributes the generated type trees omit private fields. UnityPy's strict byte
count checks remain enabled so an incomplete schema fails instead of silently
exporting incorrect data. The older Cpp2IL library bundled with the type-tree
generator cannot read this metadata version directly.

## Reproduce the export

```powershell
python helperScripts/export_client.py --game "D:\Steam\steamapps\common\Last Epoch" --assemblies ..\client-assemblies --output ..\client-export --client-version 1.5.2.2
python helperScripts/build_client_trees.py --source ..\client-export --baseline src/TreeData/1_4 --output ..\client-trees
python helperScripts/build_client_icons.py --game "D:\Steam\steamapps\common\Last Epoch" --index ..\client-export/bundle-index.json --trees ..\client-trees --output ..\client-icons
```

The first command exports core tables, the skill catalog, and 161 tree resources,
with a manifest of source hashes. Its optional `--index` argument reuses a bundle
index from the same client build. Do not reuse an index after a game update.

The tree converter excludes inactive prefab templates and uses GlobalTreeData
for point limits and prerequisites. UI components supply names, descriptions,
positions, and icons. Existing class layout anchors are retained from the
baseline. The generated trees are intermediate data: publishing a new gameplay
version also requires matching skill definitions, item data, and calculation
validation.

The icon exporter preserves decoded native RGBA pixels in seven 2048-square PNG
atlases. It verifies every sprite's pixel hash after reopening the saved atlases.
There is no resizing or lossy compression. An atlas entry keeps the existing
logical node dimensions (42, 62, or 64), independently of texture resolution.
Artwork retains its native client shape; the old small images sometimes included
baked circular frames.

To install a verified icon export, copy `ClientSprites.lua` to `src/TreeData/`
and `client-*.png` to `src/TreeData/sprites/`. The runtime shares one texture handle
per atlas and caches loaded sprites. Existing icon names are aliases only when
they match one unambiguous client sprite; other names continue to load the old
PNG. The current set contains 1,485 entries and upgrades 1,415 of the 1,661 distinct
icons used by the 1.4 trees. Entries include separate logical sizes when the same
artwork is used by different node types.

## Runtime checks

```powershell
python helperScripts/run_lua.py spec/Standalone/TreeSprites.lua
```

This checks atlas bounds, file presence, logical dimensions, shared texture
handles, sprite caching, and fallback loading. CI also runs the full application
and saved-build checks. Installing an icon export does not itself change the
active gameplay data version.

## Item conversion (staged)

```powershell
python helperScripts/build_client_items.py --source ..\client-export --baseline src/Data --output ..\client-items
python helperScripts/test_client_items.py
```

The client exporter also extracts the English localization tables. The item
converter uses their property descriptors and tooltip ordering, preserves
descending roll ranges, and records independent roll IDs for compound lines.
Historical base names are retained as `legacyNames` when the base and subtype
IDs match; the runtime resolves these without duplicating crafting entries.

The 1.5.2.2 conversion currently produces 922 named bases, 489 uniques, and 6,238
affix tiers. These outputs are intermediate files, not the active application
database. Before installing them, compare parsed modifiers against the existing
data and review combined tooltip descriptions against the underlying modifiers.
In particular, Chorus of the Anurok has different underlying roll IDs for player
and minion cold resistance despite a shared tooltip placeholder. Dragonsong's
speed tooltip refers to roll 7 while its underlying speed modifiers use roll 3.
Do not assume tooltip placeholder IDs alone prove the saved gameplay roll mapping.

Updated parsing also fixes an existing Druid mastery omission: `20% increased
health and mana` now contributes both bonuses. In the `tornado_dot` fixture,
health changes from 3,786 to 4,181 and mana from 304 to 360; its dependent defence
outputs and serialized player-stat snapshot change accordingly.

## Ability and summoned-actor prefabs

```powershell
python helperScripts/export_client_skill_prefabs.py --game "D:\Steam\steamapps\common\Last Epoch" --assemblies ..\client-assemblies --source ..\client-export --output ..\client-skills --client-version 1.5.2.2 --ability Fireball --ability Dreamslash --ability RadiantLance --ability PrimalistSummonElemental
```

This exports the selected ability prefab components, follows `ActorReference`
for summons, and resolves the summoned actor's keyed ability references through
`AbilityManager`. It walks only each prefab's object hierarchy. The example
exports six abilities and one actor, including Elemental Bolt and Geyser, and
writes a manifest with the source-file fingerprints. Unknown ability names,
ambiguous prefab roots, external actor references, and nested summons fail
explicitly instead of producing a silently incomplete export.

Keep the core export and installation on the same client build. The skill
converter checks version metadata and matching SHA-256 fingerprints for shared
source files, requiring the executable, IL2CPP metadata, and PermaLoad bundle.
It rejects mixed exports before reading property tables or writing definitions.
These raw
prefabs contain base damage and actor configuration; they do not by themselves
implement skill-tree mutations or establish the final combat calculation.

The export also records the MainPlayer ability-use component. To convert the
new 1.5 base definitions without replacing the active database:

```powershell
python helperScripts/build_client_skills.py --source ..\client-skills --core ..\client-export --output ..\client-skills-compiled
python helperScripts/test_client_skills.py
```

This produces three player skills and two Tide Elemental attacks. Cast times
use the actor's own base speed multiplier (1.1 for MainPlayer, 1.0 for the tide
elemental), multiplied by the ability's speed multiplier. Shield requirements
use the serialized `requiresSheild` field; permitted weapon IDs are resolved
through the same client's ItemList. Unknown required weapon IDs fail conversion.
Shield-requiring spells retain their spell damage calculation. The staged definitions
still require the separate runtime mutations, including Radiant Lance's block
scaling, before they can replace a complete supported gameplay version.
