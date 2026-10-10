# Intensity, volume and exit rhythm

Write the key frames first, then fill in delay and life. Describe brightness and volume as two separate curves:
brightness spikes at release, while an explosion's fire and smoke volume may peak later; a shield holds a stable
outline and only breaks at expiry. The review's pixel `energy` mixes area and value and equals neither curve.

## Every phase has a successor

| Phase | Question to answer | Common failure |
|---|---|---|
| Anticipation | does the viewer know where and when something will happen? | so big it already looks like the final blast; an impact strip polluted by the leading projectile |
| Contact or release | is this instant clearer than its neighbours? | a big white blob that lasts; contact out of step with the Lab feedback |
| Body | once the flash is gone, can you still read the action and element? | the body dies early and only sparks remain; one unchanging outline throughout |
| Secondary | do debris, smoke and sparks have cause and direction? | sprayed in every direction at once like decorative noise |
| Dissipation | is what remains still changing, and does it end on time? | an empty tail; a static dirty afterimage; a large body still visible at `duration` |

Body and secondary may overlap; they need not be five mechanically separate intervals. What is staggered are the
read points: the flash leaves first, the form takes over, debris keeps moving, smoke thins last. A later layer that
is brighter must be explained as a second hit, a return stroke or a shield break.

## Reference timings from the shipped examples

Absolute frame ranges from the example recipes (first birth to last instance's maximum life; projectiles released at
`flight`). Visible duration is decided by the image. These are not constants for every effect.

| Example | Contact or release | Main form | Afterwards |
|---|---|---|---|
| Hit Heavy (0.5 s) | Anticipation f0–3, Contact flash f2–7 | Impact burst f2–12, air bubble and wave to f14 | heavy sparks to f28, embers and dust to f30 |
| Fire Slash (0.6 s) | blade and hot edge from f1, cel crescent f2–10 | Blade body to f17, the parent swing plane to f22 | flame tongues to f35; smoke and embers end f34 |
| Magic Charge (1.5 s) | Charged flash f64–70 (the only flash) | gathering and core f0–64 | release bloom and sparks to f82–86 |
| Shield Dome (1.8 s) | raise glint f0–5 | whole shell to f84 | sphere fragments f80–104, shards to f106; clear by f108 |
| Heal (1.7 s) | — (no contact; slow fade-in) | seal f0–88, column f8–82 | plus signs and motes rise until f90–98 |
| Fire Explosion (1.3 s) | Detonation flash f9–12 | Fireball f6–40, Mushroom f12–51 | Smoke billow f14–76; check the tail at f54, 60, 66 |
| Ice Spikes (1.35 s) | Eruption glint f8–13 | crystals erupt f6–15 with overshoot, hold to about f47 | Crack glint f47–50, then shatter shards f50–78 |
| Poison Cloud (1.75 s) | Splash flash f1–4 | Burst puff f1–25, acid pool f3–104 | fumes and fog to about f99 |
| Projectile Fire (flight 0.45 s) | — (no contact) | head layers emit until release at f27 | smoke trail lives to f69 after release |
| Projectile Ice (flight 0.35 s) | muzzle rings f0–16 | lance head to f25 | shed shards and chips fall until about f41 |
| Projectile Dark (flight 0.6 s) | — (no contact) | head layers emit until release at f36 | wake and path glints live to f54 |
| Dark Vortex (1.65 s) | impact frame f62–64, release f62–70 | horizon and disk feed inward f0–62 | release arcs decay into smoke to f98; ground spiral to f88 |

Match purpose and shape before borrowing "who takes over from whom". Do not give a frequent light hit an
explosion's long smoke tail, and do not force a charge to only dim from its first frame.

## Curves must land on real frames

Recipe delay and life are 60 FPS frames; F-curve keys are percent of life. For a fixed-life layer born at d with life
L, a change at real frame t goes at key `100 × (t − d) / L`. Random life makes each instance change at a different
absolute time; use a fixed-life key layer to align with the contact.

A child's delay counts from its parent instance's birth. A parent that is born repeatedly gives every child its own
clock; read the earliest and latest births that `vfx brief-validate` expands. "This layer lives 20 frames" does not
mean it is gone at frame 20 — the last-born instance is still alive.

A projectile stops emitting at `flight` and its trail ends with each instance's life. Lengthen a smoke tail with a
longer flipbook segment, colour decay and suitable life, and re-check `duration` and the live-instance budget. Only
raising `duration` creates an empty tail; only raising life can make the sequence play out early.

## Do not gamble on the last frame

The brief marks the exit start, the middle of the exit and the clear time; review samples at least those three plus
a check frame after `duration`. Long effects may add explicit 80 % and 90 % key frames so the peak does not fill the
thumbnails while the tail gets a single empty tile.

When a shell, column or ring shows no visible break-up, first check whether the renderer supports that combination,
then consider real geometry pieces, segmented arcs or a timed hand-off between shapes. A correct compile read-back
does not mean "the dissolve works" — see the [shield case](cases.md#shield-a-break-that-never-shows-a-gap).

Each round, decide first whether you are fixing the contact, the body hand-off or the exit, and change only those
layers. Judge order and screen share in the standard strip, erosion and trails in the detail sheet, and rhythm at
full speed in the Lab.
