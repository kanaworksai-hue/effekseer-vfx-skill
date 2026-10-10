# Review loop, evidence and delivery

A still frame cannot show rhythm. After every change: `vfx lint`, `vfx build --ids <ID>`, `vfx review --ids <ID>
--note "<one problem, one change>"`, then **open the images**.

Contents: what review produces · flags · reading the strip · rounds and history · independent review ·
verification · variants · capture behaviour

## What `vfx review` produces

The Godot Lab renders the effect in a real viewport with the UI hidden, using the combat staging (two dummies at
opposite ends of the platform; the effect is performed according to its `delivery`). Frame numbers count from the
effect's own start (punch, cast, projectile arrival); dummies hold an idle pose. A projectile strip ends at arrival
and excludes its impact; an impact strip keeps the same landing point and arrival time without the incoming
projectile's residue. The command returns:

- `sheets` — the whole-timeline strip `vfx/previews/strips/<ID>.png` (at most 18 tiles; key frames are never dropped);
- `compare` — `<ID>_compare.png`, previous round above the current one, when a previous strip exists;
- `details.<ID>.sheet` — a key-frame sheet (contact neighbourhood, brief beats, body, exit and a post-duration check)
  and `details.<ID>.frames` — the full-size frames;
- `flags`, `changes` (flag kinds added or resolved since the last round, moved key timings), `metrics`,
  `history` and the `evidence` ID of this capture.

`vfx strip <ID> [--compare]`, `vfx frames <evidence_id> <frames...>` and `vfx history <ID>` re-read them later.
Look at the comparison first when one exists.

## Flags

Pixel metrics are "change energy" against the empty stage, so a large faint smoke and a small white flash are
comparable. They are a reading aid, **not** a GPU or overdraw measurement.

| Flag | Meaning | First fix |
|---|---|---|
| `barely visible` | under 0.25 % of the stage changes at the strongest frame | the body is too small or too dark |
| `dead tail` | the last 35 % has no frame above 5 % of peak energy or 0.25 % changed stage | shorten `duration` and trailing lives, or make the dissipation visible |
| `blown out` | over 10 % pure white for more than two sampled frames | smaller glow, less emissive |
| `cut off` | still clearly visible on the last frame | the duration is too short |
| `off-peak contact` | the whitest frame is more than 6 frames from manifest `peak` | move the contact or `peak`; the Lab flash and kick land elsewhere |
| `lingering flash` | near-peak white lasts over 12 frames around contact | contact should be 2–5 frames; sustained hot bodies (beam cores, spikes) do not count |
| `no white-hot core` / `washed out` | almost no pixel above 85 % brightness / almost no saturated mid-tone body at peak | add a hot core / restore the body's saturation |
| `sinks` (fire only) | the mass moves down after contact | fire should rise |
| `expands while charging` (dark only) | the radius grows before the release | dark should draw inward |

Thresholds were calibrated tile by tile on real library renders; the reasoning is at the top of
`scripts/vfxkit/review.py`. Change a threshold only after checking real strips, and add a line of reasoning there.

## Reading the strip

Flags alone are not a review. In the strip and the key-frame sheet ask:

1. Can you tell what the effect is from the first lit tile? Is the contact the brightest moment and only a few frames?
2. Is the main shape eroding or sweeping, or only scaling and fading?
3. Do secondary particles go fast then slow, in the element's direction (fire up, ice down, dark inward)?
4. Do arcs, pillars and ground decals sit on or under the dummy, not beside it or floating?
5. On a bright background (`--bright`), do the alpha-blended layers still work?

For tails, look at the middle of the last third, not just the last two tiles; fetch actual frames with
`vfx frames` or capture extra moments with `--key-frames`. One isolated smoke puff does not prove a whole exit.

## Rounds and history

Each round fixes **one class of problem** and states it in `--note`; notes, flags and key timings append to
`vfx/previews/strips/history/<ID>.jsonl`. Read the history (`vfx effect-context <ID>`) before a new round and do not
repeat a change the evidence already rejected. Iterate 3–5 rounds per effect; at the limit without a pass, report the
unresolved items instead of calling it done.

## Independent review

The author never scores its own effect. `vfx review-handoff <ID>` writes the reviewer's whole brief for the latest
fresh capture to `vfx/work/handoff/<evidence_id>.md`: the strip and key-frame images, the captured frame numbers, the
manifest entry and flags, a copy of the rubric, the path of the **vfx-review** skill when it is installed beside this
skill, and where to write the report. Give that brief, and nothing else, to a separate agent: a subagent (tell it no
more than the brief) or a new session the user opens when the host has no subagents. Not the recipe code. It writes
JSON to the `report_file`:

```json
{"id": "VFX_X", "scores": {"read": 2, "timing": 3, "layering": 2, "shape_change": 2, "motion": 2, "placement": 3, "tail": 2, "identity": 3},
 "worst": "shape_change", "fix": "one concrete change in recipe terms", "verdict": "ship"}
```

`verdict` is `iterate` when any score is below 2; `worst` must be a lowest-scoring criterion. Save it to a file and
bind it with the command `review-handoff` returned: `vfx review-submit <evidence_id> <report_file> --reviewer <reviewer id>`
(`--frames` defaults to the report's `observed_frames`).
The tool validates structure, freshness and observed frames; it cannot prove the reviewer's independence — the host
(you) must actually isolate it. If the verdict is `iterate`, apply its one fix next round.

## Verification

`vfx overview` tiles the latest standard captures into `vfx/previews/strips/overview_*.png`.
`vfx effect-verify <ID>` checks that the expanded current recipe, input textures, Core read-back, built resources,
Lab stage and images are all the ones the passing review saw, and that the overview includes this capture. Only
`verified: true` is done. A screenshot existing, no flags, or exit code 0 are not quality passes. Any change to a
recipe, texture, brief or the Lab invalidates older evidence; after updating the Lab template run
`vfx init --update-templates` first. Runtime behaviour needs its own API checks (`TestApi.gd`, see [godot](godot.md));
device performance needs device evidence.

After finishing, keep the effect library (`vfx/src`, `vfx/briefs`, textures, recipes JSON, `.efkefc`, `.efk`,
manifest, overview pages and `metrics.json`) together under version control. Per-frame captures, logs, receipts and
single-effect strips stay local (`vfx/.gitignore` written by `init` handles this).

## Variants

`--view close` changes only the inspection camera; `--profile bare` turns off the Lab bloom, impact light and
camera kick to judge the effect on its own; `--bright` uses a bright background. Each is stored separately and never
overwrites the standard/default baseline or its metrics; the baseline for verification is standard/default.

## Capture behaviour (macOS / Windows)

The user may be using the machine during a review: macOS stops drawing fully covered windows, and Godot steals focus
on launch. In capture mode the Lab keeps its window on top, parked in the bottom-right corner with only a small part
showing (the viewport still renders at 1280×800), ignores keyboard input and close requests, and the review hands
focus back to the previous app (about a 0.2 s flicker per launch). Effects that exit early or never play are
re-captured (up to 3 times).

On Windows the Lab parks its window the same way, but the review does not hand focus back: the Godot window keeps
focus until the capture ends (a two-effect review takes well under a minute). Do not minimise it while it captures.
