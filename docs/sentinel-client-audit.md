# Sentinel priority audit

Priority: Rive, Void Cleave, Abyssal Echoes, Devouring Orb, Anomaly, and Sentinel
passives, including mastery passives. Client source: 1.5.2.2, with the executable
and metadata fingerprints recorded in `client-export.md` and the export manifest.
This is an implementation checklist, not a claim of complete skill support.

## Verified ability basics

The dedicated prefab export contains Rive1, Rive2, Rive3 and the other four
abilities. The player ability-use component supplies its 1.100000023841858 speed
multiplier. `build_client_sentinel.py` validates matching source fingerprints
before updating cast time, cooldown, mana cost and weapon requirements. Existing
damage definitions remain separate from this limited conversion, except for the
three Rive strike definitions read from their respective DamageEnemyOnHit
components. Rive now exposes First strike, Second strike and Third strike through
the existing skill-part selector. Main and calculation-tab selections persist
independently in saved builds. The default is still First strike, not a weighted
full-combo estimate.

| Ability | Base mana cost | Native weapon requirement |
| --- | ---: | --- |
| Rive | 0 | None |
| Void Cleave | 15 | Two-Handed Axe or Two-Handed Sword |
| Abyssal Echoes | 35 | None |
| Devouring Orb | 18 | None |
| Anomaly | 0 | None |

```powershell
python helperScripts/export_client_skill_prefabs.py --game "D:\STEAM\steamapps\common\Last Epoch" --assemblies ..\.tools\client-dummy-attributes --source ..\client-export-1.5.2.2 --output ..\client-sentinel-export --client-version 1.5.2.2 --ability Rive1 --ability Rive2 --ability Rive3 --ability VoidCleave --ability AbyssalEchoes --ability DevouringOrb --ability Anomaly
python helperScripts/build_client_sentinel.py --source ..\client-sentinel-export --core ..\client-export-1.5.2.2 --baseline src\Data\skills.json --output src\Data\skills.json
```

## Verified Rive specialization modifiers

`RiveTree.updateMutator` (RVA `0x251e1e0`, client fingerprint above) applies
these modifiers to separate strike mutators. `SkillNodeMods.lua` matches the
exact exported node text and scopes each bonus to both Rive and its strike.

| Node | Per-point behavior | Native branch RVA |
| --- | --- | --- |
| Flurry (`sndr1-15`) | 10% increased attack speed for strikes 1 and 2 | `0x251f549` |
| Concentration (`sndr1-16`) | +1% base crit for strikes 1 and 2; +2% for strike 3 | `0x251f071` |
| Focused Strike (`sndr1-18`) | Strikes 1 and 2 cannot crit; strike 3 has double crit chance and +50% crit multiplier | `0x251eb57` |
| Brutality (`sndr1-30`) | 15% more damage for strike 3 | `0x251f357` |
| Double Slash (`sndr1-23`) | Remove strike 3 from the sequence | `0x251f041` |

The native critical-stat property IDs are 4 (crit chance) and 5 (crit multiplier).
Focused Strike calls `Stats.MoreStat` for crit chance and `Stats.AddedStat` for
the multiplier. Brutality calls `Stats.MoreStat` for damage (property 0).
Runtime tests cover point scaling/removal, combined critical modifiers, strike
switching and isolation from another skill. These do not model combo averages,
echoes or ailment inheritance. Selecting the third strike with Double Slash
now disables its calculation with an explanation. The strike selector remains
available and refunding the node restores the third strike.

### Native sequence evidence

`ComboInfo.GetAbilityFromIndex` (`0x244e830`) resolves index 0 to the base ability;
positive indices resolve to `getComboAbilities()[index - 1]`. The sequential
branch in `ComboAbilityList.incrementCombo` (`0x244c770`) increments that index,
then resets after it exceeds the maximum. Thus the base Rive1 precedes the list:

- Standard: base Rive1 + [Rive2, Rive3] = 1, 2, 3.
- Cadence: base Rive1 + [Rive2, Rive1, Rive2, Rive3] = 1, 2, 1, 2, 3.
- Double Slash removes Rive3 from that list; with Cadence the cycle is 1, 2, 1, 2.

The lists are constructed by `RiveMutator.GetCurrentComboList` (`0x2269840`).
This evidence is for the upcoming time-weighted combo calculation; individual
strike mode does not yet average these sequences.

## Mechanics still to implement and validate

- Rive: weighted combo damage and speed,
  Cadence and Double Slash sequences, remaining strike-specific modifiers,
  Temporal Warrior, Weapon Specialist and Foe Cleaver. Native prefabs give the
  first two strikes 125% added-damage effectiveness and the third 250%. The first
  two use duration 0.75 / speed 1.25; the third uses duration 0.7 / speed 1.0,
  before the player's speed multiplier. Individual strike calculations do not
  yet represent the complete combo. Native `RiveMutator.GetCurrentComboList` at
  RVA `0x2269840` selects the Cadence list through `skipEveryOtherStrike3`, and
  removes the third strike through `noStrike3`. Those sequence rules still need
  integration with weighted damage, ailment application and proc rates.
- Void Cleave: movement/use timing, charges, conditional damage, conversion,
  Resonating Cleave and its interaction with Abyssal Echoes, Ravaging Aura.
- Abyssal Echoes: Abyssal Decay, chains/repeats, direct-hit conversion, buffs and
  damage-over-time consumption. The prefab's 0.3-second lifetime is not evidence
  of the ailment's duration.
- Devouring Orb: collision versus Void Rift/Abyssal Orb damage, emission rate,
  orbiting duration, consumed orbs, and global buffs.
- Anomaly: return effects, Time Bubble uptime and buffs, instant variants,
  Future Strike and Time Rot. In the staged 1.5 tree, Void Maw grants 10%
  increased health leech per point, versus 50% in the old 1.4 tree.
- Sentinel passives: verify parsed modifiers against gameplay, mastery effects,
  echo chance and echo damage, ailment interactions and conditional bonuses.
  Matching tooltip text between versions is not proof of implemented behavior.

The 1.5 tree remains staged. Basic ability fixes are global, as are the existing
skill definitions; this change does not enable 1.5 as the default tree version.
