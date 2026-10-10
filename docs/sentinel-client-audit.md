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
full-combo estimate. A separate sidebar summary now shows Rive Combo Hit DPS,
Combo Attacks/sec and Combo Duration for a continuous sequence, with separate
Combo Bleed DPS and Combo Ignite DPS rows when applicable. The summary
sums each strike's damage and time, including strike-specific speed and critical
modifiers. It does not replace selected-strike DPS or Full DPS: integrating
other ailments, triggered abilities and echoes across the cycle remains
unfinished. These separate components are not total build damage.

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
| Cadence (`sndr1-21`) | Change the sequence to 1, 2, 1, 2, 3 | `0x251ec07` (dispatch); `0x2269840` (list) |
| Sever (`sndr1-9`) | +50% ignite chance on strike 1 | `0x251ee8f` |
| Twisting Fangs (`sndr1-10`) | +50% ignite chance on strike 2 | `0x251efb5` |
| Massacre (`sndr1-31`) | +25% bleed chance on all strikes; 10% increased bleed duration on strike 3 | `0x251f42f` |

The native critical-stat property IDs are 4 (crit chance) and 5 (crit multiplier).
Focused Strike calls `Stats.MoreStat` for crit chance and `Stats.AddedStat` for
the multiplier. Brutality calls `Stats.MoreStat` for damage (property 0).
Runtime tests cover point scaling/removal, combined critical modifiers, strike
switching and isolation from another skill. These do not model combo averages,
echoes or ailment inheritance. Selecting the third strike with Double Slash
now disables its calculation with an explanation. The strike selector remains
available and refunding the node restores the third strike.

Massacre calls `Stats.AilmentChanceStat` with ailment ID 2 and 0.25 per point
for each strike, then `Stats.AilmentDurationStat` with 0.10 per point only for
strike 3. The latter's argument is increased duration. The trigger calculation
evaluates `AilmentDuration_<ailment ID>` against the source hit before passing
the evaluated increase to the ailment's duration modifiers. This preserves
source skill/strike restrictions. Ignite bonuses above 100% retain multiple
expected applications per hit; tests cover 150%, strike switching, duration
scaling/refunds and isolation from Fireball's bleed.

### Native sequence evidence

`ComboInfo.GetAbilityFromIndex` (`0x244e830`) resolves index 0 to the base ability;
positive indices resolve to `getComboAbilities()[index - 1]`. The sequential
branch in `ComboAbilityList.incrementCombo` (`0x244c770`) increments that index,
then resets after it exceeds the maximum. Thus the base Rive1 precedes the list:

- Standard: base Rive1 + [Rive2, Rive3] = 1, 2, 3.
- Cadence: base Rive1 + [Rive2, Rive1, Rive2, Rive3] = 1, 2, 1, 2, 3.
- Double Slash removes Rive3 from that list; with Cadence the cycle is 1, 2, 1, 2.

The lists are constructed by `RiveMutator.GetCurrentComboList` (`0x2269840`).
`CalcRiveCombo.lua` calculates each distinct strike in an isolated calculator
environment without changing either saved strike selection or overwriting the
selected strike's cached output. For each occurrence, time is 1 / attack rate;
damage is strike DPS multiplied by that time. Combo hit DPS is total damage
divided by total time, rather than the arithmetic mean of strike DPS values.
Runtime tests cover all four Cadence/Double Slash combinations with Flurry,
Concentration, Focused Strike and Brutality, plus selection/cache isolation.

Bleed and ignite are evaluated separately for each applying strike, with that
strike's trigger chance and source-specific duration. An isolated source
override avoids reading the currently selected strike from the global cache.
Temporary ailment calculations do not publish cache entries or add saved skill
groups. For these stacking ailments, each strike's sustained DPS is weighted
by its fraction of cycle time; this retains the lifetime damage of applications
that continue ticking during subsequent strikes. Tests compare all four
Cadence/Double Slash sequences against independently selected-strike outputs,
including a selected third strike with no ignite of its own.

The summary still uses the planner's existing ailment damage model. Remaining
source-damage inheritance and feedback from debuff stacks must be audited before
claiming complete combo/build DPS support. Other ailments and echo applications
are not included in these two rows.

## Mechanics still to implement and validate

- Rive: integrate the combo summary with full DPS, ailments and triggers;
  remaining strike-specific modifiers,
  Temporal Warrior, Weapon Specialist and Foe Cleaver. Native prefabs give the
  first two strikes 125% added-damage effectiveness and the third 250%. The first
  two use duration 0.75 / speed 1.25; the third uses duration 0.7 / speed 1.0,
  before the player's speed multiplier. Individual strike calculations do not
  yet represent the complete combo's ailments or proc rates. Native `RiveMutator.GetCurrentComboList` at
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
