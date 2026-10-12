"""VFX_Kaiju_Atomic_Beam: a sustained atomic breath that the game aims and sweeps (Vfx.beam()).

Example from the effekseer-vfx skill. Copy it with `vfx examples add`, then edit, build and review it
like any other effect; its historical review does not carry over to your edits.
"""
from vfxkit.primitives import *


def recipe():
    pale = (230, 246, 255, 255); blue = (60, 150, 255, 255); rim = (25, 60, 220, 130)
    breath = beam('Breath', pale, blue, rim, width=.55, interval=6, flow=.06, origin=1.1, end=1.5, sparks=6,
                  steam=(205, 215, 225, 150), steam_life=(40, 50), scorch=(170, 215, 255, 220), scorch_life=50)
    # What the beam touched keeps smouldering after it shuts off: dark smoke left along the raked path (inherits the hit
    # point only at birth) that thins slowly and carries the last third of the effect (reviews found it empty).
    hit_point = breath[-1]
    hit_point['children'].append(smoke('Breath smoulder', (58, 54, 52, 175), count=1, size=(.9, 1.2), grow=1.8, life=(56, 60), speed=(.003, .006),
                                       rise=.0002, texture='T_SmokeSheet02', inherit=TRAIL, soft=.3, color_end=(58, 54, 52, 120), fade_out=8,
                                       spawn=dict(shape='Sphere', radius=[0, .2], rotate=False), rotation=[0, 0, [-12, 12]], spin=[0, 0, [-.1, .1]],
                                       flipbook=dict(x=4, y=4, frame_length=6, loop='Once')))
    return effect('Kaiju_Atomic_Beam', 'Kaiju Atomic Beam', 'beam', 'atomic', 2.52, [
        *breath,
        # Ignition: the contact frame at the mouth and a shock bubble that the beam punches out of.
        flash('Ignition flash', WHITE, 2.2, life=5, delay=1),
        shell('Ignition shell', (150, 205, 255, 200), 1.2, life=14, delay=1),
    ], attach='caster', peak=.03, impact=.6, light=(.55, .75, 1), delivery=dict(kind='beam', charge='VFX_Kaiju_Atomic_Charge'),
        hold=1.5, inputs=beam_inputs(160), scale='kaiju',
        design='A white-hot line inside a saturated blue beam with a wide dim rim; noise streams outward along it, steam, sparks, cooling scorch and smouldering smoke stay where it lands, and it stays locked to its end point while the game rakes it.')
