"""VFX_Kaiju_Explosion: a photographic, building-sized fuel explosion for a kaiju battle (realistic, not stylised).

Example from the effekseer-vfx skill. Copy it with `vfx examples add`, then edit, build and review it
like any other effect; its historical review does not carry over to your edits.
"""
from vfxkit.primitives import *

# Colours sampled from daylight photographs of fuel explosions (references/realism.md): the core is a pale
# yellow-white, not pure white; the body is orange, the cooling edge a deep red-orange; soot is a warm near black
# and the smoke column a brown-grey that is lighter where the sun hits its top.
CORE = (255, 244, 214, 255)
FIRE = (255, 168, 72, 255)
EDGE = (214, 84, 28, 255)
SOOT = (38, 32, 29, 235)
SMOKE = (92, 84, 78, 215)
DUST = (150, 136, 118, 170)


def recipe():
    floor = -1.3   # the impact anchor sits 1.35 m above the floor (before scale)
    fire = ramp((0, FIRE), (40, EDGE), (75, (120, 40, 18, 160)), (100, (60, 20, 10, 0)))
    return effect('Kaiju_Explosion', 'Kaiju Explosion', 'explosion', 'fire', 2.3, [
        heat_haze('Heat haze', 4.2, life=70, delay=2, strength=.7),
        # Draw order back to front: the smoke column and the soot body come before the fire, so the fire burns in front
        # of its own smoke instead of being punched out by it.
        # The column outlives the fire: it keeps being fed for the first second, holds most of its density over life
        # (colour_end keeps 40% alpha) and is still climbing and widening when the effect ends.
        smoke('Smoke column', SMOKE, count=9, size=(2.3, 3.0), grow=2.0, life=(84, 90), delay=8, interval=5, speed=(.004, .009), rise=.00012,
              texture='T_SmokeSheet02', position=[0, .4, 0], soft=.5, color_end=fade(SMOKE, 90), fade_out=24,
              # rotate=False: the velocity stays world-up; with the default sphere rotation each puff flies off along
              # its own random spawn direction and the column drifts sideways and sinks.
              spawn=dict(shape='Sphere', radius=[0, .6], rotate=False),
              # Photographic smoke is lit from above: keep the lit tops up (a full random roll turns puffs upside down
              # and swings the off-centre billows sideways).
              rotation=[0, 0, [-12, 12]], spin=[0, 0, [-.1, .1]],
              # A slower flipbook stops before the sheet's last, nearly empty cells: the column is still dense at the end.
              flipbook=dict(x=4, y=4, frame_length=8, loop='Once')),
        sprite('Soot body', 'T_FireballSootSheet01', SOOT, color_end=fade(SOOT), life=70, delay=5, size=3.2, size_curve=[[0, .45], [25, .9], [100, 1.2]],
               blend='Blend', billboard='RotatedBillboard', rotation=[0, 0, 20], flipbook=dict(x=4, y=4, frame_length=4, loop='Once'),
               velocity=[0, .006, 0], fade_in=2, fade_out=30),
        # The white-hot moment is the contact flash alone (one spike); the fireball starts orange on its third cell.
        sprite('Fireball', 'T_FireballSheet01', **fire, life=58, delay=1, size=3.0, size_curve=[[0, .25], [18, .85], [100, 1.15]],
               billboard='RotatedBillboard', rotation=[0, 0, 20], flipbook=dict(x=4, y=4, frame_length=4, start=2, loop='Once'),
               velocity=[0, .005, 0], fade_in=0, fade_out=14, emissive=.85),
        # Secondary lobes rolling off the main ball: the silhouette breaks up instead of growing as one disc.
        sprite('Fire lobes', 'T_FireballSheet01', **ramp((0, FIRE), (60, EDGE), (100, (90, 30, 12, 0))), count=3, life=[40, 52], delay=4,
               size=[1.2, 1.7], billboard='RotatedBillboard', rotation=[0, 0, [-180, 180]], flipbook=dict(x=4, y=4, frame_length=3, loop='Once'),
               **spray([[-1.5, 1.5], [.2, 1.6], [-.6, .6]], .2), fade_in=0, fade_out=12, emissive=1.6),
        flash('Contact flash', CORE, 4.5, life=4, delay=1),
        # Short: the white contact is one spike; by frame 8 (20 at kaiju time) the orange body has taken over.
        glow('Bloom', (255, 190, 110, 140), 3.5, life=6, delay=1),
        # Ground dust skirt rolling out along the floor and the shock ring that throws it.
        dict(name='Ground pivot', renderer='None', life=120, position=[0, floor + .05, 0], children=[
            smoke('Dust skirt', DUST, count=10, size=(1.4, 1.9), grow=1.8, life=(60, 90), delay=4, speed=(0, 0), rise=.0002,
                  rotation=[0, 0, [-12, 12]], spin=[0, 0, [-.1, .1]],
                  spawn=dict(shape='Circle', radius=[.4, .8], division=8), travel=dict(end=[[2.4, 3.4], 0, 0], easing='EaseOutCubic'),
                  texture='T_SmokeSheet02', soft=.35),
        ]),
        shock_ring('Shock ring', (255, 210, 160, 150), 6.0, life=16, delay=2, ground=True, position=[0, floor + .08, 0]),
        distortion_ring('Shock refraction', 5.0, life=16, delay=2, strength=1.0),
        *spark_burst('Embers', 18, (255, 200, 120, 255), (200, 70, 20, 255), distance=(1.6, 3.6), life=(24, 40), delay=2, gravity=.0012),
        debris('Debris', 8, [[-3.0, 3.0], [.6, 3.0], [-1.2, 1.2]], color=(46, 41, 38, 255), size=(.1, .22), life=(50, 80), gravity=.0035,
               floor=floor + .05, delay=2),
    ], attach='impact', peak=.03, impact=.9, light=(1, .72, .45), delivery=TARGETED, scale='kaiju',
        design='A pale yellow-white flash becomes an orange fireball rolling up out of its own soot, lobes break off it, a dust skirt rolls along the ground and a brown-grey smoke column keeps climbing after the fire is gone.')
