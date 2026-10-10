# Comparing against a reference clip

Requires `ffmpeg` and `ffprobe`. Only use clips the user provides or is allowed to use; record where they came from.

1. `vfx reference-import <clip.mp4> --start 0 --end 2 --slow 2 [--roi x y w h] [--source-url <url>]` decodes at most
   30 media seconds into the ignored `vfx/work/references/`. `--slow 2` means the clip plays at half speed, so effect
   time = clip time relative to `--start` ÷ 2. Open the returned `overview` image. Put the reference ID and times in
   the brief's `reference` field.
2. Read the labelled frames in order and write anticipation, contact, body, secondary and exit into the brief's
   beats. For detail use `vfx reference-frames <reference_id> <start> <end> --count 8` on one short span instead of
   reloading the whole clip. If the clip's speed is unknown and the rhythm depends on it, ask.
3. After a review, `vfx reference-compare <reference_id> <evidence_id> --times 0.1 0.3` pairs reference moments with
   the exact captured Godot frames (capture missing ones with `vfx review --key-frames`). Compare rhythm, outline,
   screen share, saturated body, dark layers and residue. Each view keeps its own aspect ratio and time label; never
   make them "the same size" with an unstated crop or scale.

The analysis is approximate: compression, background and bloom change pixels; camera moves or cuts pollute changed
area. For moving cameras use manual key frames and an explicit ROI. Do not infer world size, emissive values,
particle counts or invisible textures from video; mark approximations in the brief. Reference observations guide
shape and rhythm; they never override the measured units, UV, HDR and inheritance rules of this engine.
