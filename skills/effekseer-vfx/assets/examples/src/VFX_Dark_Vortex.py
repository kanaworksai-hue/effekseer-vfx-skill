"""VFX_Dark_Vortex: Dark impact played where VFX_Projectile_Dark arrives: a black hole that feeds, then releases.

Example from the effekseer-vfx skill. Copy it with `vfx examples add`, then edit, build and review it
like any other effect; its historical review does not carry over to your edits.
"""
from vfxkit.primitives import *


def recipe():
 violet=(150,60,255,255); magenta=(225,120,255,255); pale=(245,225,255,255); ash=(118,108,126,170); ember=(255,125,45,230)
 # A volume, not a screen sticker: a black horizon inside a torn accretion disk lying in a tilted 3D plane (far half
 # drawn behind the horizon, near half across it; the Godot plugin ignores effect depth writes, so draw order does the
 # occlusion), broken wisp strokes swirling round it at random tilts, ground dust and rocks dragged in, then one release.
 DISK=[-72,0,0]   # nearly flat, tipped 18 degrees toward the camera: an ellipse in perspective
 GROUND=-.93      # floor height below the body anchor (Lab: body sits 0.95 m up)
 grow=[[0,.6],[20,1],[85,.9],[100,.05]]   # opens fast, then only contracts: dark draws inward
 def disk(tag,sweeps,colors=((200,105,255,230),(250,175,255,255))):
  # Accretion disk half as broken strands in the disk plane: each sweep is redrawn every 16 frames at two radii and
  # tightens toward the horizon over its life, so the disk churns and feeds instead of sitting there as a clean dish.
  return [wisps(f'{tag} {i}',colors[i%2],(1.9,1.35)[i%2],count=4,interval=16,width=(.55,.3)[i%2],sweep=sweep,life=(22,26),delay=2*i,tilt=DISK,size=1,
   size_curve=[[0,1.2],[100,.7]],flow=-.07,broken=.12,emissive=(1.4,1.9)[i%2]) for i,sweep in enumerate(sweeps)]
 def swirl(tag,color,radius,width,delay,**kw):
  # Six partial strokes per layer, redrawn every 9 frames at a new tilt near the disk plane: the charge swirls and crosses.
  return wisps(tag,color,radius,count=6,interval=9,width=width,sweep=(0,170),life=(16,22),delay=delay,tilt=((-80,40),(0,360),(-45,45)),size=1,
   size_curve=[[0,1.15],[100,.35]],flow=-.06,**kw)
 release_wave=[wisps('Release arc A',(215,150,255,220),3.0,count=1,width=.55,sweep=(0,200),life=18,delay=62,tilt=DISK,size=1,broken=.15),
  wisps('Release arc B',pale,1.3,count=1,width=.3,sweep=(360,170),life=16,delay=63,tilt=[DISK[0],0,40],size=1,broken=.15)]
 return effect('Dark_Vortex','Dark Vortex','element','dark',1.65,[
  glow('Back glow',(120,40,255,110),3.0,life=62,size_curve=[[0,1.15],[80,.8],[100,.2]],fade_in=4,fade_out=5),  # behind the horizon; contracts while feeding
  # Ground: grey dust and dark rocks are dragged in along the floor toward the hole while it feeds.
  smoke('Inflow dust',(150,140,155,165),count=7,size=(.6,.95),grow=.6,life=(30,38),interval=7,spawn=dict(shape='Sphere',radius=[0,.01],rotate=False),rise=0,
   travel=dict(start=[[-2.4,2.4],GROUND,[-1.6,1.6]],end=[0,GROUND+.15,0],easing='EaseInCubic')),
  *disk('Disk far',[(-85,10),(-20,80)]),
  swirl('Swirl back',(170,80,255,230),1.7,.45,0),
  sprite('Event horizon','T_Dot01',(0,0,0,215),life=62,size=1.5,size_curve=grow,billboard='Billboard',blend='Blend',fade_in=4,fade_out=3),
  glow('Hot singularity',pale,.45,life=60,size_curve=[[0,.2],[60,.8],[90,1.3],[100,.4]],fade_in=6,fade_out=4,emissive=1.8),
  wisps('Photon wisps',pale,.95,count=3,interval=20,width=.09,sweep=(0,120),life=(22,26),tilt=((-12,12),(-12,12),(0,360)),size=(.85,1.0),flow=-.1,emissive=1.6),
  *disk('Disk near',[(95,200),(170,265)]),
  swirl('Swirl front',(245,170,255,255),1.3,.32,4,emissive=2.4),
  distortion_ring('Gravitational lensing',2.6,life=62,strength=1.4,size_curve=grow,fade_in=6,fade_out=4),
  sprite('Rubble infall','T_Shard01',(120,108,112,255),count=6,interval=6,life=[34,44],blend='Blend',rotation=[0,0,[-180,180]],spin=[0,0,[-14,14]],size=[.14,.28],size_end=.05,
   travel=dict(start=[[-2.6,2.6],[GROUND,GROUND+.3],[-1.4,1.4]],end=[0,0,0],easing='EaseInCubic'),fade_in=2,fade_out=4),
  # Infall: a spinning pivot in the disk plane carries particles that ease from the outer disk into the hole -> spirals.
  dict(name='Infall pivot',renderer='None',life=62,rotation=[DISK[0]+90,0,0],spin=[0,-7,0],children=[
   motes('Disk matter',26,pale,color_end=violet,life=(18,26),interval=2,size=(.12,.24),spawn=None,
    travel=dict(start=[[-2.4,2.4],[-.12,.12],[-2.4,2.4]],end=[0,0,0],easing='EaseInQuadratic'),turbulence=.0004),
   radial_sparks('Disk streaks',16,pale,color_end=magenta,life=(12,16),interval=3,length=(.7,1.2),width=.08,emissive=2.0,spawn=None,
    travel=dict(start=[[-2.2,2.2],[-.1,.1],[-2.2,2.2]],end=[0,0,0],easing='EaseInCubic'))]),
  # Impact frame: the stage drops to near-black on the release frames and the white burst fires over it (drawn after),
  # the anime "black frame + white flash" beat.
  sprite('Impact frame','T_SoftCircle',(4,0,10,215),life=2,delay=62,size=26,billboard='Billboard',blend='Blend',fade_in=0,fade_out=1),
  # Contact: a narrow hot disk rim preserves the absorptive centre; the slice carries the brightest accent.
  wisps('Collapse rim',pale,.8,count=1,width=.095,sweep=(0,285),life=5,delay=62,tilt=DISK,size=1,broken=.1,emissive=2.0),
  sprite('Collapse core','T_Smoke02',(8,2,18,245),life=8,delay=61,size=1.2,size_curve=[[0,1],[35,.85],[100,.12]],billboard='Billboard',blend='Blend',cutoff=dict(start=0,end=.7,easing='Linear'),fade_in=0,fade_out=4),
  glow('Release bloom',(150,60,255,140),4.0,life=18,delay=62),
  slice_line('Slice line',pale,10,width=.07,angle=-14,life=14,delay=62),
  slice_line('Cross line',(225,150,255,255),5.5,width=.045,angle=68,life=10,delay=64),
  # The release lies down on the disk plane as two torn strokes sweeping opposite ways, then goes out as grey smoke arcs.
  *release_wave,*[decay(arc,ash,lag=6,stretch=1.65) for arc in release_wave],
  decal('Ground spiral','T_Vortex01',magenta,4.2,life=26,delay=62,spin=4,color_end=fade((110,90,120,255)),position=[.35,GROUND,.2],alpha_texture='T_NoiseTile01',cutoff=dict(start=.2,end=.65,easing='Linear'),fade_in=0,fade_out=16,emissive=1.4),
  decal('Spiral brand','T_Vortex01',(70,62,78,190),4.4,life=30,delay=68,spin=1.2,blend='Blend',position=[.35,GROUND+.01,.2],alpha_texture='T_NoiseTile01',cutoff=dict(start=.15,end=.6,easing='Linear'),fade_in=4,fade_out=18),
  # Complementary accent: a hot orange rim under the near side of the release, 5-10% of the frame.
  wisps('Ember rim',ember,2.1,count=1,width=.22,sweep=(100,265),life=16,delay=62,tilt=(-90,0,0),size=1,position=[0,GROUND+.05,0],broken=.12,emissive=1.6),
  distortion_ring('Release refraction',4.4,life=14,delay=62,strength=1.1),
  radial_sparks('Release needles',14,pale,color_end=violet,distance=(1.4,3.6),life=(14,28),length=(.6,1.3),delay=62),
  # Ground pivot: eased travel ends are local positions, so floor-level rolls live under a node sitting on the floor.
  dict(name='Ground pivot',renderer='None',life=99,position=[0,GROUND+.25,0],children=[
   smoke('Residue',ash,count=7,size=(.7,1.1),life=(26,32),delay=64,spawn=dict(shape='Circle',radius=[.3,.8],rotate=True,division=7),
    travel=dict(end=[[1.0,1.9],0,0],easing='EaseOutCubic'),rise=.0003)]),
  motes('Afterglints',10,(255,215,255,255),color_end=violet,life=(26,32),delay=66,distance=(.6,2.2),size=(.08,.16),texture='T_Star01',turbulence=.002),
 ],attach='body',peak=1.05,impact=.9,light=(.7,.35,1),delivery=dict(kind='projectile',projectile='VFX_Projectile_Dark'),
 design='A black horizon inside a torn tilted accretion disk; broken wisp strokes swirl round it at shifting tilts while ground dust and rocks are dragged in. Two dark impact frames, then a long slice line, two torn disk-plane arcs with an orange under-rim and a branded ground spiral; the light goes out as grey smoke arcs and glints.')
