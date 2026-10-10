# Category skeletons

Skeletons give layer roles and timing relationships; trim them to the game's style. Pick one main shape, then only
the supporting layers it needs. A light hit can be very simple; a finisher may have several stages. Every category
below has a complete, independently reviewed example (`vfx examples show <name>` prints its layer plan with absolute
frames and roles; `vfx examples add <name>` copies it into the project): `hit`, `slash`, `charge`, `shield`, `heal`
and the projectile + impact pairs `fire`, `ice`, `poison`, `dark`.

## Hit

Reference: example `hit` (`VFX_Hit_Heavy`). A short anticipation concentrated on the contact point, a brief flash and a jagged burst first, then directional
speed lines and tiered sparks, ending with dust or a little smoke. The white flash makes the contact felt; the body
conveys force. Not every hit needs a big ring and dark smoke.

| Role | Primitive | Alternatives |
|---|---|---|
| anticipation | shrinking `glow` | a few inward lines |
| contact | `flash` | a short hot shape with an outline |
| body | painted burst `sprite` with `POP` + `DISSOLVE`, `tilted_ring(..., tilt=(0,58,0))` | `shell` air bubble |
| secondary | `spark_burst` (two or three tiers, one spray direction) | `radial_sparks` with `spray` |
| exit | `smoke` dust, `motes` embers | quick falling dust; never seconds for one hit |

If only thin needles remain after the peak, lengthen or strengthen the body. If it looks like fireworks, narrow the
emission and `travel` directions before adding particles. Budget ≤ 60.

## Slash

Reference: example `slash` (`VFX_Slash_Fire`). A `swing()` pivot defines a tilted swing plane, yawed about ±30–40°
so the arc reads as an ellipse cutting through space; `slash_set()` puts afterimage, body and hot edge inside it
(`slash_arc` at three widths: wide dim afterimage lagging two frames, saturated body, thin white edge), a refraction
arc behind the blade, and a painted cel crescent held for a few frames. The crescent is `billboard='Fixed'` and lies
in the blade's own plane (same lean), rotated by the texture's measured bulge (`SLASH02_BULGE`), so it tilts with the
swing instead of facing the camera. Sparks stagger along the arc. Fire exits with
peeling flame and rising embers, physical with short metal sparks, ice with a hold and a shatter. Changing element
changes motion and material, not just colour.

Keep the arc's negative space between layers. The target's chest is only the placement anchor: the arc's visual
midpoint also depends on the texture's bulge, the rotation and the pivot — measure with `vfx texture-info`. If the
tail is still a whole crescent, fix the sweep and erosion before adding a smoke afterimage.

## Explosion

Reference: example `VFX_Fire_Explosion`. A Gather and Inward fuse tighten at the target, a short Detonation flash
releases, the Fireball and rising Mushroom take over, directional debris and sparks carry the impact, and the Smoke
billow, dust and ground marks give weight.

The fire must keep saturated volume after the flash — not just an expanding ring or many small bright dots.
Organise secondary motion along the shot, the ground or upward; not every layer doing the same spherical motion.
Smoke draws behind the fire and takes over the cooled shape; if smoke covers the centre, check order and density
first. Ground marks say where it landed, rising volume says it erupted; a bigger full-screen glow cannot replace
either. Look at f18–42 for the hand-off and f54–66 for the smoke, not only the peak.

## Projectile

Reference: pairs `fire`, `ice`, `poison` and `dark` (`VFX_Projectile_Fire`, `VFX_Projectile_Ice`,
`VFX_Projectile_Poison`, `VFX_Projectile_Dark`). Head layers (Fireball,
Hot core) follow the handle; a Comet tail gives the head direction; Flame trail, Smoke trail and Embers use
`inherit=TRAIL` and stay on the path. A wide tail, a thin hot line and short shed particles need different lives;
head and path must both read.

Check launch, mid-flight, arrival, after arrival and clear. With a fixed flight time, trail density comes from the
emission interval and particle life together. Changing head inheritance changes spatial relationships — do not
cover a rigid tube by lengthening the trail. The impact is a paired effect: review the projectile strip and the
impact strip separately, and the full exchange in the Lab. Budget ≤ 100.

## Charge and release

Reference: example `charge` (`VFX_Magic_Charge`): about one second of inward build (f0–64), one release f64–70,
release sparks to about f86. `motes` and `radial_sparks` with negative `travel` gather inward, two `orbit_band` rings in different tilted planes
build volume, a core and aura accumulate, and a release flash, `shell` and sparks give one clear release. Camera and
stage feedback may strengthen the release, but the gathering itself must be readable.

A ring that only spins in Z without internal flow becomes a rotating icon; use UV flow (`alpha_scroll`), tilted
planes and inward travel. If the release is huge and the anticipation weak, build a visible gathering path first
instead of raising all brightness.

## Shield and sustained status

Reference: example `shield` (`VFX_Shield_Dome`) and the shield case in [cases](cases.md). A short raise glint, a `mesh` sphere `shell` and rim for sustained volume, surface flow, scan bands and glints to keep
the hold alive. At the end the whole shell hands over to `shell_fragments` with real gaps; fragment motion and colour
decay make the exit.

Stable does not mean flashing every frame, nor a full sphere that switches off at once. Check first that the
character reads inside the shell, then the surface flow and the exit. The six sphere fragments are the verified
solution here; whether other materials can really dissolve must be tested separately.

## Heal and buff

Reference: example `heal` (`VFX_Heal`). A ground `decal` seal states ownership, a `column` builds slow rising volume, rising rings, symbols and life `motes`
carry the meaning, and a glow and twinkles close it. Do not make a heal an attack with a violent white flash and
bursting debris. It can be soft or pulse, but it must keep an outline and stay visible in the standard camera. A
white peak is not this category's pass criterion; use the rubric's purpose exceptions.

## Using the example code

`vfx examples show <name|ID>` prints the full layer plan with absolute frames and roles; `vfx examples add <name>`
copies the source, brief and painted textures into the project. Adapt a copy under a new ID rather than editing an example
in place when you want to keep it as a baseline. The examples' historical scores describe the skill's own renders,
not your build: build, review and get an independent score again after any change. Two examples were judged
`iterate` (see `vfx examples`, `historical_review.worst`); they still teach their pattern, and their weakest point is
a good first exercise.
