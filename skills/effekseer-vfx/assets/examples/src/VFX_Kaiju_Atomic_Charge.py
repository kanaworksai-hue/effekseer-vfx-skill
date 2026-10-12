"""VFX_Kaiju_Atomic_Charge: dorsal plates light up from the tail to the head before an atomic breath.

Example from the effekseer-vfx skill. Copy it with `vfx examples add`, then edit, build and review it
like any other effect; its historical review does not carry over to your edits.
"""
from vfxkit.primitives import *

# Plates on the caster dummy's back surface, from the hips to the back of the head, then the mouth, relative to the
# caster anchor (1.2 m above the feet, Lab metres; scale='kaiju' makes the chain about 30 m long). The dummy faces +x, so
# its back is at x = -0.27. A game with a real monster replaces these with its plate positions.
SPINE = [(-.27, -.36, 0), (-.29, -.2, .03), (-.3, -.04, -.03), (-.29, .12, .03), (-.27, .27, -.02), (-.2, .42, .02)]
MOUTH = (.45, .1, .12)   # where the Lab's beam leaves the caster (VfxLab MUZZLE)


def recipe():
    pale = (225, 245, 255, 255); blue = (70, 150, 255, 255); deep = (30, 70, 220, 200)
    # One plate every 8 frames (20 at kaiju time): the lit column is still climbing when the mouth starts to gather.
    step = 8
    chain = charge_chain('Plates', SPINE + [MOUTH], blue, pale, step=step, until=64, width=.32, glow=.34, restrike=3)
    # Each plate throws a few sparks as it ignites: the climb reads as a chain of small discharges, not a fade-in.
    kicks = [radial_sparks(f'Plate {i + 1} sparks', 4, pale, color_end=blue, distance=(.12, .3), life=(8, 12), delay=i * step, width=.04,
                           length=(.12, .22), position=list(at)) for i, at in enumerate(SPINE)]
    # Each plate is a solid shape that switches on: a six-sided crystal fin leaning up and back from the spine. The whole
    # row is there, dim blue-grey, from the first frame (so the read is "plates on a back" at once); each fin pops white
    # when its turn comes, then holds a steady blue with a slow flicker. Separate lit fins make the climb read step by
    # step. On a real monster whose plates glow through their material, drop the fins and keep the arcs.
    # Emissive stays below 1: brighter fins overlap into one bloom blob and the separate shapes are lost.
    fin = (40, 95, 230, 255); dim = (70, 90, 120, 110); life = 72

    def fin_curve(born):
        lit = 100 * born / life
        stops = ([(0, dim), (lit, dim)] if lit > 0 else []) + [(lit + 2, pale), (lit + 12, fin), (min(99, lit + 40), (70, 130, 245, 255)), (100, fin)]
        return ramp(*stops)['color_curve']
    fins = [crystal(f'Plate {i + 1} fin', fin, .3 + .045 * min(i, 4), .08, life, edge=(150, 210, 255, 255),
                    position=[at[0] - .04, at[1], at[2]], rotation=[0, 0, 55], fade_in=0, fade_out=6, emissive=.7,
                    color_curve=fin_curve(i * step))
            for i, at in enumerate(SPINE)]
    return effect('Kaiju_Atomic_Charge', 'Kaiju Atomic Charge', 'charge', 'atomic', 1.35, [
        # Ionised air around the back thickens as the plates light: a dim volume the arcs crackle through.
        glow('Back glow', deep, 1.2, life=66, delay=4, position=[-.3, .02, 0], size_curve=[[0, .3], [70, 1], [100, 1.15]], fade_in=20, fade_out=6),
        *fins, *chain, *kicks,
        # The mouth gathers the charge at the end of the chain: a saturated blue body round a small white core,
        # gone a few frames after the flash so nothing lingers as a static orb.
        glow('Mouth body', blue, .8, life=28, delay=40, position=list(MOUTH), size_curve=[[0, .2], [85, 1], [100, 1.3]], fade_in=8, fade_out=4, emissive=1.4),
        glow('Mouth core', pale, .35, life=26, delay=42, position=list(MOUTH), size_curve=[[0, .2], [85, 1], [100, .6]], fade_in=6, fade_out=3, emissive=2.2),
        # Energy drawn into the mouth for the last second: streaks spawn on a shell round it and accelerate inward,
        # faster and denser toward the release, so the mouth gathers rather than just swelling.
        # They hang under a pivot at the mouth: with rotate=True emission, `travel` (and a `position`) are in each
        # particle's rotated frame, so a position on the streak itself scattered them outward.
        dict(name='Mouth pivot', renderer='None', life=66, position=list(MOUTH), children=[
            radial_sparks('Mouth gather', 30, pale, color_end=blue, life=(10, 14), delay=40, interval=.8, width=.06,
                          length=(.25, .4), spawn=dict(shape='Sphere', radius=[.6, .8]), easing='EaseInCubic',
                          travel=dict(end=[0, [-.78, -.6], 0], easing='EaseInCubic'), fade_in=2, fade_out=3, emissive=2.0)]),
        motes('Ion motes', 22, pale, color_end=blue, life=(14, 22), interval=2, size=(.04, .08), delay=6, radius=(0, .2),
              spawn=dict(shape='Sphere', radius=[.05, .2]), position=[-.32, .02, 0], distance=(.15, .4), turbulence=.002),
        flash('Charged flash', WHITE, 2.4, life=5, delay=64, position=list(MOUTH)),
        # The release throws sparks forward along the coming beam and leaves a short-lived afterglow on the plates.
        radial_sparks('Release sparks', 14, pale, color_end=blue, distance=(.4, 1.1), life=(10, 16), delay=64, position=list(MOUTH), width=.05),
        glow('Plate afterglow', deep, 1.0, life=16, delay=64, position=[-.3, .02, 0], fade_in=0, fade_out=12),
    ], attach='caster', peak=1.07, impact=.35, light=(.55, .75, 1), delivery=SELF, scale='kaiju',
        design='Crystal plates on the back switch on one by one from the hips to the head, each with a spark and an arc jumping to the next, and stay lit, until the mouth gathers a blue glow and one flash hands over to the beam.')
