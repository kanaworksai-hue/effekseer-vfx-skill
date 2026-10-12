"""World scale: write a recipe at the Lab's character scale and build it for a much larger world (giants, kaiju).

Primitives, defaults and craft numbers are tuned for a ~1.75 m character in a 1-unit = 1 m world. A recipe that
declares `scale` keeps those numbers and is converted when `effect()` returns it:

- space x `world`: sizes, positions, travel, spawn radii, velocities, accelerations, gravity, floor heights,
  soft-particle distances;
- time x `time`: life, delay, interval, fades, flipbook frame lengths and the effect's duration/peak/flight/hold;
  rates (velocity, spin, UV scroll) divide by it and accelerations by its square.

Why time stretches: a scaled-up explosion that keeps its character-scale timing reads as a miniature. Froude
similarity says time should grow with sqrt(world); film and games compromise near world ** 0.25 so that a 40x
kaiju blast lasts 2.5x longer instead of 6.3x (references/scale.md). Profiles carry the agreed numbers; a dict
gives your own.

Only top-level layers are scaled in space: children live in their parent's coordinate frame and inherit its scale.
Numbers in `bind` scale; equation strings (`'@In0'`) are world distances the game supplies and stay as they are;
in a product `[k, '@In1']` only the constant k scales.
"""
import copy
import math

# world: units per Lab unit; time: duration multiplier; budget: particle budget multiplier (bigger screens need more
# pieces for the same density); camera: Lab stage scale (same as world unless a profile wants a closer look).
PROFILES = {
    'character': dict(world=1.0, time=1.0, budget=1.0),
    'giant': dict(world=8.0, time=1.7, budget=2.0),      # 14 m creatures, siege machines; time ~ world ** 0.25
    'kaiju': dict(world=40.0, time=2.5, budget=3.0),     # 70 m monsters, warships, mecha; time ~ world ** 0.25
}
TIME_KEYS = ('life', 'delay', 'interval', 'fade_in', 'fade_out')
RATE_KEYS = ('uv_scroll', 'alpha_scroll', 'distortion_scroll', 'blend_scroll')


def profile(scale):
    """Normalise `scale` ('kaiju', a number for world, or {'world','time','budget'}) to a full profile dict."""
    if scale is None:
        return None
    if isinstance(scale, str):
        if scale not in PROFILES:
            raise ValueError(f'Unknown scale profile {scale!r}; use one of {sorted(PROFILES)} or a dict with world/time')
        return dict(profile=scale, **PROFILES[scale])
    if isinstance(scale, (int, float)) and not isinstance(scale, bool):
        scale = dict(world=float(scale))
    if not isinstance(scale, dict) or set(scale) - {'world', 'time', 'budget', 'profile'}:
        raise ValueError('scale must be a profile name, a number (world) or a dict with world, time and budget')
    world = float(scale.get('world', 1))
    if not world > 0:
        raise ValueError('scale world must be positive')
    out = dict(profile=scale.get('profile', 'custom'), world=world, time=float(scale.get('time', round(world ** .25, 3))),
               budget=float(scale.get('budget', max(1.0, round(world ** .3, 2)))))
    if not out['time'] > 0 or not out['budget'] >= 1:
        raise ValueError('scale time must be positive and budget at least 1')
    return out


def _map(value, f):
    """Apply f to a number, a [min, max] range or a list of those."""
    if isinstance(value, (list, tuple)):
        return [_map(v, f) for v in value]
    return f(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else value


def _frames(value, t, minimum=0):
    return _map(value, lambda v: max(minimum, round(v * t, 3)))


def _life(value, t):
    # Core stores life as integer frames; rounding down keeps every layer inside the stretched duration.
    return _map(value, lambda v: max(1, math.floor(v * t + 1e-9)))


def _time(layer, t):
    if 'life' in layer:
        layer['life'] = _life(layer['life'], t)
    for key in TIME_KEYS[1:]:
        if key in layer:
            layer[key] = _frames(layer[key], t)
    if isinstance(layer.get('flipbook'), dict) and 'frame_length' in layer['flipbook']:
        layer['flipbook']['frame_length'] = max(1, math.floor(layer['flipbook']['frame_length'] * t + 1e-9))
    for key in RATE_KEYS:
        if key in layer:
            layer[key] = _map(layer[key], lambda v: v / t)
    if 'spin' in layer:
        layer['spin'] = _map(layer['spin'], lambda v: v / t)


def _space(layer, s, t, top):
    """Scale lengths by s and convert per-frame rates for the time stretch t. `top`: the layer's own frame is world."""
    k = s if top else 1.0
    vel, acc = k / t, k / (t * t)
    if top:
        if 'size' in layer:
            layer['size'] = _map(layer['size'], lambda v: v * s)
            if 'size_end' in layer:
                layer['size_end'] = _map(layer['size_end'], lambda v: v * s)
        elif 'scale_start' in layer:
            start = layer['scale_start']
            layer['scale_start'] = _map([start] * 3 if isinstance(start, (int, float)) else start, lambda v: v * s)
            if 'scale_end' in layer:
                end = layer['scale_end']
                layer['scale_end'] = _map([end] * 3 if isinstance(end, (int, float)) else end, lambda v: v * s)
        elif 'scale' not in (layer.get('bind') or {}):
            layer['scale_start'] = [s, s, s]
        for key in ('position',):
            if key in layer:
                layer[key] = _map(layer[key], lambda v: v * s)
        travel = layer.get('travel')
        if isinstance(travel, dict):
            for key in ('start', 'end'):
                if key in travel:
                    travel[key] = _map(travel[key], lambda v: v * s)
        spawn = layer.get('spawn')
        if isinstance(spawn, dict):
            for key in ('radius', 'start', 'end', 'noise'):
                if key in spawn:
                    spawn[key] = _map(spawn[key], lambda v: v * s)
        bind = layer.get('bind')
        if isinstance(bind, dict):
            # Numbers are Lab-scale constants; equation strings are world values supplied by the game.
            for key, value in bind.items():
                bind[key] = [v * s if isinstance(v, (int, float)) and not isinstance(v, bool)
                             else [v[0] * s, v[1]] if isinstance(v, (list, tuple)) else v for v in value]
    if 'velocity' in layer:
        layer['velocity'] = _map(layer['velocity'], lambda v: v * vel)
    if 'acceleration' in layer:
        layer['acceleration'] = _map(layer['acceleration'], lambda v: v * acc)
    for force in layer.get('forces') or []:
        if force.get('type') == 'Gravity' and 'gravity' in force:
            force['gravity'] = _map(force['gravity'], lambda v: v * acc)
        elif 'power' in force:
            force['power'] = force['power'] * vel
        if top and 'position' in force:
            force['position'] = _map(force['position'], lambda v: v * s)
    # World-coordinate quantities scale on every level.
    if isinstance(layer.get('collide'), dict) and isinstance(layer['collide'].get('height'), (int, float)):
        layer['collide']['height'] = layer['collide']['height'] * s
    if isinstance(layer.get('soft'), (int, float)) and not isinstance(layer.get('soft'), bool):
        layer['soft'] = layer['soft'] * s


def _layers(layers, s, t, top=True):
    for layer in layers:
        _time(layer, t)
        inherit = layer.get('inherit') or {}
        # A child that does not bind its parent's scale lives in world units again.
        _space(layer, s, t, top or inherit.get('scale') == 'NotBind')
        _layers(layer.get('children', []), s, t, top=False)


def apply(entry, scale):
    """The effect entry converted to the world of `scale`, with the profile recorded under entry['scale']."""
    p = profile(scale)
    entry = copy.deepcopy(entry)
    s, t = p['world'], p['time']
    _layers(entry['layers'], s, t)
    for key in ('duration', 'peak', 'flight', 'hold'):
        if isinstance(entry.get(key), (int, float)):
            entry[key] = round(entry[key] * t, 4)
    if isinstance(entry.get('arc'), (int, float)):
        entry['arc'] = entry['arc'] * s
    entry['scale'] = p
    return entry


def factors(recipe):
    """(world, time, budget) of a built recipe; (1, 1, 1) at character scale."""
    p = recipe.get('scale') or {}
    return float(p.get('world', 1)), float(p.get('time', 1)), float(p.get('budget', 1))
