# Shipped examples

Four ranged pairs (a projectile plus the impact played where it arrives), five single effects, one per common
category, and the kaiju set. They are complete production recipes with design briefs, painted textures (processed copies) and the
prompts that made them. Their layer roles are the category skeletons in [skeletons](skeletons.md).

| Pair | Projectile | Impact | What it teaches |
|---|---|---|---|
| `fire` | `VFX_Projectile_Fire` — boiling flipbook fireball, stretched comet tail, world-space flame and smoke trails | `VFX_Fire_Explosion` — lopsided fireball thrown along the shot, climbing mushroom, ground licks decaying into smoke, scorch and cracks | flipbook billows, colour ramps, `decay()`, directional `spray`/`debris` |
| `ice` | `VFX_Projectile_Ice` — crystal lance with a navy backing, prism-fringed ribbon, frost rings frozen on the path | `VFX_Ice_Spikes` — crystals erupting with overshoot, a hold with climbing halos, a timed shatter | `crystal` meshes, fresnel edges, value backing, hold-then-break rhythm |
| `poison` | `VFX_Projectile_Poison` — lobbed glossy glob (deformed mesh) with a wet highlight, acid thread, drips that land | `VFX_Poison_Cloud` — acid splash, spreading pool with bubbles, fumes cooling to murky purple-grey, rolling fog | `arc`, Track trails, `ShapeNoise` liquid, complementary dark core, floor collision |
| `dark` | `VFX_Projectile_Dark` — alpha-black churning orb inside crossing magenta wisps, needles and dust dragged in | `VFX_Dark_Vortex` — black horizon in a tilted accretion disk that feeds, a black impact frame, then torn release arcs and a ground spiral | absorptive Blend body, inward `travel`, two-half disk occlusion, impact frame |

| Single | Effect | What it teaches |
|---|---|---|
| `hit` | `VFX_Hit_Heavy` | two-frame anticipation, 5-frame contact, dissolving jagged burst, three `spark_burst` tiers, air bubble and refraction wave |
| `slash` | `VFX_Slash_Fire` | `slash_set()` (afterimage, body, hot edge, refraction, cel crescent) inside a yawed `swing()` plane; flame tongues peeling off |
| `charge` | `VFX_Magic_Charge` | a one-second inward build with tilted `orbit_band` rings and imploding shells, then exactly one release |
| `shield` | `VFX_Shield_Dome` | fresnel shell and thin rim, overshoot pop, hold with scan bands, `shell_fragments` break that clears on time |
| `heal` | `VFX_Heal` | no impact frame: floor seal, scrolling column, rings, plus signs and motes that all rise and ease out |

| Set | Effects | What it teaches |
|---|---|---|
| `kaiju` | `VFX_Kaiju_Atomic_Charge`, `VFX_Kaiju_Atomic_Beam`, `VFX_Kaiju_Explosion` | `scale='kaiju'` (built 40x larger and 2.5x slower, [scale](scale.md)); `charge_chain()` climbing the dummy's back; a sweepable `beam()` driven by game inputs with steam and scorch left behind; a photographic explosion with soot, a rising smoke column and soft ground dust ([realism](realism.md)) |

The kaiju set is staged between 70 m dummies (the Lab scales its stage with the effect) and its beam is raked from
the ground in front of the target onto its chest, after the charge.

```sh
vfx examples                     # list with historical scores and verdicts
vfx examples show slash          # layer plan, absolute frames, roles, budget (a pair shows both effects)
vfx examples add kaiju           # a set: the charge, the beam and the explosion
vfx examples add fire            # copy into vfx/src, vfx/briefs, vfx/textures/processed, vfx/texture_prompts.json
vfx lint --ids VFX_Projectile_Fire VFX_Fire_Explosion
vfx build --ids VFX_Projectile_Fire VFX_Fire_Explosion
vfx review --ids VFX_Projectile_Fire VFX_Fire_Explosion --note "baseline"
```

The historical scores (0–3 per rubric criterion) come from an independent review of renders in the skill's default
capsule Lab: two reviewers that saw only the strips, key-frame sheets, manifest entries and flags. Eleven were judged
`ship`; `VFX_Projectile_Ice` (flat lance without a white core or dark rim, no shape change in flight) and
`VFX_Projectile_Dark` (nothing stays on the path after arrival) were judged `iterate`. The kaiju set was reviewed the
same way on its own renders in the scaled Lab and all three were judged `ship` after several rounds (the reviewers'
fixes: plates on the body, discrete lit fins, an inward mouth gather, smouldering smoke and a column that outlives
the fire to fill the tails). `vfx examples` lists every
example's weakest criterion and the reviewer's one fix (`historical_review.worst`). The scores are a reference,
**not** verification of your build: re-build, review and score again. Adding an example never overwrites existing
files unless `--force`.

To make a new effect from an example, copy the source to a new ID (rename the file and the `effect('...')` name, and
its brief's `effect_id`), then change shape, motion and rhythm — not only colour (see [craft](craft.md)). Keep the
projectile/impact pairing consistent: the impact's `delivery.projectile` must name the projectile's ID.
