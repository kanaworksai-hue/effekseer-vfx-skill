# Motion and paths

A projectile plans three roles: a **head** that follows the handle, a **trail** left in world space, and **shed
particles** that fall off the path. Emit with `sustain()` and keep trails with `inherit=TRAIL`; on arrival the game
calls `stop_root()` and they dissipate naturally. The head needs a clear outline; trails differ in length and value;
a launch-moment speed line or short ring helps the viewer read the speed.

A slash shows its path with a real plane and a sweep (`swing()` + `slash_arc`), then staggers secondary emission
along the arc. Secondary particles go from fast to slow with eased `travel`; Drag does not damp PVA velocity (see
[engine conventions](engine-conventions.md)). Work out the rotated local axis before writing `travel`: sphere and
circle emission have different radial axes.

Diagnose volume and path separately: a thin trail can be fine, but the head must not become a volumeless dot. The
projectile's own strip ends at arrival and does not include its impact; the Lab's normal play shows the full pair.

Motion is not just scale. Change the main shape with sweeps, erosion, UV flow, rotating pivots and deformation;
organise debris, smoke and motes by element direction: ice holds then shatters, dark draws in, fire rises, poison
sinks slowly — each supported by consecutive frames.

The runtime provides straight and parabolic (`arc`) paths. Curved paths, volleys or sustained beams need a brief and
a runtime extension first; never tell the user a tool or API exists that this skill does not have.

## Put speed into shape and rhythm

| Visible problem | First check | First change |
|---|---|---|
| projectile looks like a floating ball | is there a direction change and a speed carrier at launch? | short swept-back wind lines, directional sparks or tails of different lengths |
| trail looks like a plastic tube | is it uniform width, flat colour, all layers the same life? | give the texture negative space; separate a short hot tail from a long soft one |
| sparks float at constant speed | does `travel` go fast then slow? | EaseOut, then gravity or light motion takes over |
| slash looks like a sticker in front of the camera | is there a real tilted plane, a sweep and emission following it? | fix the plane and sweep first, then stagger details along the arc |
| debris looks like regular fireworks | same size, same birth frame, spherical symmetry? | tier sizes and rhythm; organise the main motion along the direction of action |

A speed carrier exists so the viewer reads direction; it does not have to be a new particle group. If the trail or
shape already does the job, keep it simple. An element may pause, but the pause must lead to a clear action: ice
crystals stop growing and then shatter; dark energy gathers and then releases.

Equal angle ranges do not make light and dark particles match. Geometry pairs use fixed parameters; diagnose motion
misalignment with the steps in [layering](layering.md). A smoke afterimage may deliberately move on a different
rhythm, but say so in the brief.
