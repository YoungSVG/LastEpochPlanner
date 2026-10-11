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

Brutality's untagged damage multiplier also applies to ailments inflicted by
strike 3. In client 1.5.2.2, `ChanceToApplyAilmentsOnHit.Apply` (`0x2185c70`)
passes `GetStats()` to `AilmentApplication.Apply` with `scaleWithStats = true`.
The overload at `0x282c850` forwards those stats to
`AilmentReceiver.ApplyAilment` (`0x2830ef0`), which calls
`DamageStats.buildDamageStats` at `0x283198c` using the ailment's base damage,
its tags (including `AT.Ailment`, bit 25), and the supplied stats. Brutality's
`Stats.MoreStat` has property Damage and no tag restriction, so it remains
eligible. The planner explicitly forwards this audited multiplier through
`SourceAilmentDamage`, evaluated against the applying strike. It does not copy
all source damage modifiers, which could duplicate global bonuses or import
hit-only modifiers. Tests cover bleed and ignite, point scaling/refunds,
global damage modifiers, other skills and weighted combo bleed.

Iron Reach (`sndr1-26`) is handled by `RiveTree.updateMutator` at `0x251e91d`.
At `0x251e986`, the `Stat` constructor receives Damage, no tags, zero added/
increased value and 0.25 more damage per point; the stat is added to the second
strike's list (`r12`). The following instructions add 0.25 per point to the
second strike's area accumulator. Both bonuses now use strike-2 restrictions,
and the untagged damage multiplier is also forwarded to its ailments. Tests
cover 1/4/0 points, all three strikes, bleed/ignite, another skill and the combo
with Iron Reach and Brutality allocated together.

Azure Crescendo (`sndr1-7`, native branch `0x251ea91`) adds 0.12 more untagged
damage per point to the third strike and 5 mana per point to its
`manaToRestoreIfHits` field. `Rive3Mutator.Mutate` at `0x2268217` assigns that
amount to the hit-resource component and sets `limittedTimes = true` and
`remainingTimes = 1`. The planner applies the damage multiplier to strike 3
and its ailments and represents the mana gain with strike-3 `ManaOnHit`.
The combo mana-on-hit row uses one hit opportunity per occurrence and divides
expected mana gained by cycle duration. It is a single-target calculation;
multi-target hit probability, mana caps and echo recovery are not modelled.
Tests cover damage/bleed, unchanged maximum mana, 1/3/0 points, all four
sequences and isolation from Fireball. Ordinary mana regeneration is separate.

Triple Threat (`sndr1-22`, native branch `0x251ed08`) adds 0.50 more untagged
damage to the third strike at `0x251ed71`, 0.50 to property 45
(`IncreasedStunChance`) in the same strike's stat list at `0x251edd2`, and 0.50
to its area accumulator. The planner scopes damage, ailment damage, area and
the offensive stun increase to strike 3. The sidebar explicitly labels the
latter **Increased Stun Chance**: it is a modifier, not the final probability
against an enemy. Enemy health, stun avoidance and reactive immunity still
need a native stun calculation; no stun uptime or guaranteed stun is assumed.
Tests cover strike switching, bleed inheritance, modifier removal and skill
isolation. The stun modifier is hit-only and is not inherited by bleed.

Coup de Grace (`sndr1-32`) sets 0.15 per point in the tree branch at
`0x251ee10`; `0x251fc92` writes this to `Rive3Mutator.cullPercent` (offset
`0x1cc`). `Rive3Mutator.Mutate` at `0x2267af5` and `0x2267b88` applies it to
the third strike's base damage component. The client node reminder specifies
that competing item/passive kill thresholds use the highest value. The
planner uses a hit-only, strike-3 `CullPercent` MAX modifier, retaining the
existing selected-strike culling estimate. The combo row reports the largest
threshold among strikes actually present; Double Slash removes this node's
threshold. It does not multiply combo hit/ailment DPS or assume instant
access to strike 3 when a target crosses the threshold. Tests cover competing
10%/20% thresholds, all four sequences, refunds and skill isolation.

Savagery (`sndr1-13`, branch `0x251f312`) adds 0.15 per point to
`moreDamageAgainstIgnited` (offset `0x128`) on all three Rive mutators
at `0x251fb66` onwards. The second-strike mutation at `0x2266571` builds
a conditional effect with ailment ID 1 (Ignite) and the damage multiplier,
then attaches it to the strike's damage holders; the third strike also
reads the field at `0x2267d11`. This is a hit effect, not an inherited
ailment stat. An exact node override replaces the generic parser's incorrect
Ignite skill-name restriction with an enemy-Ignited condition and Hit flag.
Runtime coverage checks all strikes and combo hit DPS with the condition
on/off, point scaling/refunds, unchanged bleed/ignite DPS and Fireball isolation.

Champion (`sndr1-2`, native branch `0x251f6e2`) adds 0.08 more untagged damage
and 0.10 increased stun chance per point to each of the three strike lists.
The damage constructors are at `0x251f74b`, `0x251f807`, `0x251f8c3`; the
property-45 constructors are at `0x251f7ac`, `0x251f868`, `0x251f924`.
Unlike strike-specific modifiers, Champion's ordinary SkillId restriction
already matches an ailment's `groupSource`. It must not additionally use
`SourceAilmentDamage`, which would square its multiplier. Tests cover 4/1/0
points, hits/bleed/ignite with global increased damage, combination with
Brutality and Triple Threat, and isolation from Fireball.

### Native stun formula (not yet integrated)

Client `Stunned.listenForStunEvent` at `0x1667e20` receives the hit damage,
attacker stun increase and attacker duration increase. After state/immunity
checks, the arithmetic at `0x1668047` through `0x1668116` is:

```
effectiveHealth = maxHealth + currentWard
if boss: effectiveHealth *= 1 + bossEffectiveHealthModifierVsStun
chance = (2 * flatDamage * (1 + attackerStunIncrease) / effectiveHealth
          - (max(0, stunAvoidance) + 500) / 5000)
         * (1 + increasedChanceToBeStunned)
```

Values here are fractions, not percentages. The random-chance routine at
`0xf6a6d0` returns false for values <= 0 and true for values >= 1; values
between those bounds are compared against the generated random fraction.
`BaseHealth.maxHealth` is at offset `0x90`; `ProtectionClass.ward` is
at `0x170`. Inherited `PrecalculatedStatsHolder` fields at `0x70` and `0x74`
are stun avoidance and increased chance to be stunned. The boss modifier is
read from `GlobalPlayerProperties` offset `0x84` by the getter at `0x27fbdd0`.
The 1.5.2.2 asset in `PermaLoad.bundle`, path ID `5042677237873432156`, contains
`bossEffectiveHealthModifierVsStun = 0.5` (and the same value for freeze).
The core exporter now includes this class, so future exports retain the
serialized constant and source fingerprint rather than hardcoding a guessed
boss multiplier. Boss effective health is therefore `(maxHealth + ward) * 1.5`
for this client. Do not substitute current health,
ignore ward, or assume the same effective health for bosses.

The duration branch at `0x1668135` through `0x1668170` passes
`(baseDuration + addedDuration) * (1 + defenderDurationIncrease +
attackerDurationIncrease) * (1 + moreDuration)` to `Stunned.stun`.
It does not establish sustained stun uptime: immunity and state transitions
are separate gates.

`DamageStats.buildDamageStats` reads property 45 only for hits and accumulates
its added values when the tags apply (`0x108f6a9`). Its final branch at
`0x108fa40` can transform that increase as `3 * increase + 2` or
`2 * increase + 1`, depending on a local classification byte. The first form
is equivalent to tripling `1 + increase`, not adding a flat 200 percentage
points after the final chance formula. Classification and caller damage
semantics still need tracing; constants named for player melee/non-melee
damage are insufficient evidence to apply these branches unconditionally.

`CharacterStats.SetInitialValues` (`0x1695070`) supplies the player-specific
marker: at `0x1695730` through `0x1695765`, it calls the stat modifier setter
with property 45, value 1, modification type 1, tags `0xA00` (Melee | Bow),
and override enabled. The exported MainPlayer `CharacterStats` component has
an empty serialized `stats` list; this modifier is initialized in code and
cannot be recovered by reading that prefab alone. In `buildDamageStats`, a
positive increased-value field on property 45 with exactly these tags sets
the local classification byte to 1 at `0x108f70e`. The byte-2 branch remains
unproven and must not be selected just from the name of a melee constant.

The caller also matters: `ProtectionClass.ApplyDamage` (`0x1122a10`) passes
its running damage total in `xmm15` to the stun event at `0x1125628`. This
total is accumulated after per-type mitigation (`0x11242a1`), multiplied by
ordinary block mitigation (`0x11244ae`) and the damage-taken buff
(`0x11244f5`), then adjusted by mana-before-ward (`0x11245eb`) and the later
health/endurance path (`0x1124ac2`). Ward is written before the stun event
(`0x1124823` in the fully absorbed path); `TryGainBossWard` is also called
before it (`0x1124adf`). The listener therefore reads ward at the time of the
event, after that hit's ward processing, not necessarily the pre-hit ward.
The event is gated by a surviving target and hit damage (`0x1125591` through
`0x11255be`). A calculator must distinguish these stages and handle critical
and noncritical outcomes separately before averaging clamped probabilities.

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
