# Client-derived defence formulas

## Ordinary block

Source: installed Last Epoch **1.5.2.2**, Steam app 899770, build 25816319,
Unity 6000.4.8f1, IL2CPP metadata version 39. Read-only analysis; the game was
not modified or executed to extract the formula.

- GameAssembly.dll SHA-256: `d5f9fb458f0e9878e697a92b590a586a52fd77e645f8bf87bb4f2b74c6c56567`
- global-metadata.dat SHA-256: `81ff3419726bb5cf8e4f86eace2b2df2638ec4bc6ffed8a7a5dbaf09aa6f7bed`
- Client build hash: `8dfd6929fe2d10f2e77b7ed4c8e6910f49b2736b`
- Method: `PrecalculatedStatsHolder.blockMitigation`, RVA `0x11223f0`.

For effectiveness `B > 0` and area/enemy level `L`, let `a = L + 5`:

```
damage reduction = 0.6 * (0.0006*B*B + 1.2*B) / (0.0006*B*B + 1.2*B + 60*a)
                 + 0.25 * (3*B) / (3*B + 0.03*a*a + 40)
```

Nonpositive effectiveness gives zero reduction. This is a fraction; the
planner exposes percentages. At 3,000 effectiveness and level 100 it prevents
59.305% of a blocked hit, not 100%. Lua double precision can differ slightly
from the client's single precision near rounding boundaries.

The previous calculation treated ordinary block as complete damage avoidance,
independent of effectiveness. Expected incoming damage now uses
`1 - blockChance * damageReduction`, with both inputs expressed as fractions.
The maximum unblocked hit calculation is unaffected. This equation covers
ordinary block only; special item/skill overrides require separate verification.

The client guide (`GameGuide.Block_Paragraph_1`) describes a block roll for
every hit. The planner therefore uses the same chance for each incoming hit
category rather than dividing it by four for the default average category.
The chance is bounded to 0..100%; the old default maximum was zero because
no base maximum was supplied. The explicit untyped configuration continues
to bypass block.

Restoring a nonzero block chance also makes health/mana recovery on block
reachable. That path no longer references an absent Energy Shield pool.
The six saved-build snapshots were regenerated and reviewed: offensive values
are unchanged; the throwing build now receives its 83% block chance and
50.405% mitigation, so its estimated survival improves. The other five builds
only change block metadata and have unchanged effective health.

Run the independent checks from the repository root:

```
luajit spec/Standalone/DefenceMath.lua
```

On Windows the bundled runtime can be used instead:

```
python helperScripts/run_lua.py spec/Standalone/DefenceMath.lua
```
