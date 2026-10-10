# Design briefs

Every new effect starts with a brief: write `vfx/briefs/<ID>.json` before the recipe. `vfx brief-validate <ID>`
checks the brief against the recipe (layer paths, beats inside the duration), so run it once the first recipe draft
exists, and again after every change to either. For a small fix, read the existing brief and adjust the affected goals. Brief times are absolute
60 FPS frames from the start of the effect; the manifest keeps seconds.

## What the brief decides

State the **purpose** (frequent hit, single skill, finisher, sustained status, showcase piece), the **shape the
player reads first**, its **size relative to a character** in the standard camera, the **release or contact
moment**, and **what remains at the end**. Acceptance lines describe visible behaviour — "the fire keeps rolling
upward after the flash is gone" — never "more layers" or "premium feel".

Start with three key frames: **earliest readable**, **body takes over from the contact**, **last intentional
residue**. For each, say what shape is where and how it is changing, then pick primitives. "A tilted arc across
the target's chest, fire peeling off its lower edge and rising, ending in embers only" guides code far better than
"cool fire slash".

| Purpose | Shape read first | Volume and scale decision | Space to keep clear |
|---|---|---|---|
| Frequent hit | small burst and short directional lines | centred on the hit point; never covers the whole character every time | the player's body and surrounding combat information |
| Directional slash | arc and hot edge in a tilted plane | the swing plane passes through the target; width and negative space both visible | the character silhouette inside and behind the arc |
| One explosion | a volume erupting from the contact point | the body visibly grows, lifts and leaves residue in the standard camera | lanes outside the body for secondary motion |
| Sustained status | a stable outline around its owner | does not hold the highest brightness; the hold has surface motion | the character inside the shell and the main view |

Do not compose from texture names. The same smoke sequence can carry weight after a fireball or residue along a
flight path, but birth position, size, direction, density and played frame range must differ. When important
layers share a centre, state which is in front, which behind and which exits first.

## Palette roles

`palette` assigns **core**, **body**, **dark** and **matter** (accent optional). A short hot core; a saturated body
with an outline; a dark that gives contrast to the outline or residue; smoke and debris that give the effect
material weight. Declare accents in the brief rather than adding a colour per layer. The effect should still read
in greyscale. See [layering](layering.md).

## Time structure by purpose

A normal hit is a short contact, then decay. A charge may build gradually. Lightning may have an explicit return
stroke. A shield may hold a stable stretch. A multi-hit skill states each peak separately. An explosion's brightness
may fall while its body still grows and rises. A swarm of small sparks never replaces a body that disappeared.
See [timing](timing.md).

## Exceptions to the style rules

"Irregular" suits matter, breakage and brush strokes; it does not automatically apply to seals, aiming cues or
optical stars. "Many roles" suits complex skills, not light hits. A "white core" helps an attack contact; it does not
mean a heal must flash. The reference techniques in [craft](craft.md) are candidate tools; the user and the brief
decide style and purpose. Do not give every skill the same glow, shock ring and sparks after reading one table.

## Brief format

All fields except `reference` are required (`assets/brief.schema.json`). Abbreviated from the shipped
`VFX_Fire_Explosion` brief, which plans all 24 layers:

```json
{
  "schema_version": 1,
  "effect_id": "VFX_Fire_Explosion",
  "role": "paired ranged impact",
  "style": "stylized anime combat",
  "dominant_shape": "turbulent comet and ascending cooling smoke",
  "palette": {"core": [255, 250, 220], "body": [255, 120, 30], "dark": [60, 30, 20], "matter": [125, 110, 100]},
  "delivery": {"kind": "projectile", "projectile": "VFX_Projectile_Fire"},
  "anchor": "body",
  "beats": [
    {"frame": 4, "name": "gather", "expect": "Inward gathering at target"},
    {"frame": 10, "name": "contact", "expect": "White-hot detonation lasts only a few frames"},
    {"frame": 18, "name": "body", "expect": "Orange fire survives white flash"},
    {"frame": 54, "name": "tail", "expect": "Grey smoke thins while ascending"}
  ],
  "layer_plan": [
    {"name": "0:Scorch", "role": "ground footprint", "primitive": "Sprite T_Crack01", "exit": "gone by absolute f55"},
    {"name": "5:Detonation flash", "role": "contact", "primitive": "flash", "exit": "gone by absolute f12"}
  ],
  "acceptance": ["Head/body silhouette reads at standard camera after the brightest accent"],
  "avoid": ["Large persistent white blob erasing the body"]
}
```

- `effect_id`, `delivery` and `anchor` must equal the recipe's `id`, `delivery` and `attach`.
- `beats` are ordered absolute frames (0 … duration + 12); review always captures them as key frames.
- `layer_plan[].name` is the layer's **full indexed path** — sibling index and name, children joined by `/`
  (`0:Swing plane/1:Blade body`) — so duplicate names stay distinguishable. Update it when layers move. Every layer
  should be planned (unplanned ones are warned about). Never put brief metadata into a layer dict.
- `brief-validate` expands parent birth times: a child's delay is not the effect's start.

The shipped examples (`vfx examples add <pair>`) each come with a complete brief to copy from.

## Before you start

Colour, emissive, Add/Blend and the Lab's HDR bloom together decide the picture; know the stage settings in
[engine conventions](engine-conventions.md). Use the existing library and the dummy's size as the first scale, then
check the standard camera. Strong reference work is a target for rhythm and silhouette; its size and brightness
numbers are not this engine's defaults.
