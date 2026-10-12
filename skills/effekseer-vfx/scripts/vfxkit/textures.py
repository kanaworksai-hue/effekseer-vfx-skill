"""Deterministic math primitives: glows, rings, tileable noise, trails, distortion maps.

Complex hand-painted shapes (flame, slash, rune, smoke...) come from an image generation model and
are only post-processed; nothing here imitates them. Originals are never overwritten.
"""
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from .paths import ROOT
from .ownership import guard
# Procedural textures saved by procedural() outside masks(): the noise sprite, the cross, and the distortion maps.
EXTRA_PROCEDURAL={'T_Noise01','T_Cross01','T_Distort01','T_Distort02','T_DistortRing01','T_DistortHaze01'}

def spectral(n,beta=2.0,stretch=(1,1),seed=0):
 """Seamlessly tileable 1/f noise in 0..1; stretch>1 smears along that axis (y,x)."""
 rng=np.random.default_rng(seed)
 fy=np.fft.fftfreq(n)[:,None]*stretch[0]; fx=np.fft.fftfreq(n)[None,:]*stretch[1]
 f=np.sqrt(fx*fx+fy*fy); f[0,0]=1
 field=np.fft.ifft2(np.fft.fft2(rng.standard_normal((n,n)))/f**beta).real
 lo,hi=np.percentile(field,[1,99])
 return np.clip((field-lo)/(hi-lo),0,1)

def worley(n,cells=6,seed=0):
 """Tileable cellular noise: 0 at feature points, 1 on cell borders."""
 rng=np.random.default_rng(seed); pts=rng.random((cells*cells,2))
 y,x=np.mgrid[0:1:complex(n),0:1:complex(n)]; best=np.full((n,n),9.0)
 for py,px in pts:
  dy=np.abs(y-py); dx=np.abs(x-px)
  best=np.minimum(best,np.hypot(np.minimum(dy,1-dy),np.minimum(dx,1-dx)))
 return np.clip(best*cells*1.1,0,1)

def masks(n=256):
 y,x=np.mgrid[-1:1:complex(n),-1:1:complex(n)]; r=np.sqrt(x*x+y*y); angle=np.arctan2(y,x)
 v=(y+1)/2; u=(x+1)/2  # v: 0 top .. 1 bottom
 out={
 'T_SoftCircle':np.clip(1-r,0,1)**2,
 'T_Glow01':np.exp(-(r/.33)**2)*np.clip(1-r,0,1)**.5,
 'T_Dot01':np.clip((.62-r)/.08,0,1),
 'T_Ring01':np.exp(-((r-.72)/.035)**2)*(r<.95),
 'T_RingSoft01':np.clip((r-.35)/.45,0,1)**2.2*np.clip((.92-r)/.06,0,1),
 'T_Streak01':np.clip(1-np.abs(x),0,1)**1.7*np.exp(-(y/.045)**2),
 'T_Star01':np.maximum(np.exp(-(x/.035)**2)*np.exp(-(y/.55)**2),np.exp(-(y/.035)**2)*np.exp(-(x/.55)**2)),
 'T_Flare01':np.clip(np.exp(-(y/.02)**2)*np.exp(-(x/.6)**2)+np.exp(-(x/.03)**2)*np.exp(-(y/.25)**2)+np.exp(-(r/.12)**2),0,1),
 'T_Spark01':np.clip(1-np.abs(x)/.35-np.abs(y)/.85,0,1)**.7,
 'T_Shard01':np.clip(np.minimum((y+.85)/.25,(.9-np.abs(x)*3.2-y*.55)/.12),0,1),
 'T_Bubble01':np.exp(-((r-.62)/.04)**2)*.8+np.exp(-(((x+.25)**2+(y+.3)**2)/.009)),
 # Tileable alpha masks for dissolve (alpha texture) and scrolling detail.
 'T_NoiseTile01':spectral(n,1.7,seed=11),
 'T_NoiseTile02':1-worley(n,5,seed=5)**1.4,
 'T_NoiseStreak01':spectral(n,1.5,stretch=(1,9),seed=23),
 'T_NoiseStreak02':np.clip(spectral(n,1.5,stretch=(9,1),seed=29)*1.3-.1,0,1),  # vertical streaks for columns
 }
 # Trail band for Ring/Track/Model UVs: U runs along the motion, V=0 is the sharp leading edge.
 streak=spectral(n,1.4,stretch=(1,7),seed=31)
 out['T_Trail01']=np.clip(.25+streak*1.1,0,1)*np.clip(v/.06,0,1)*(1-v)**1.15*np.clip(1-u,0,1)**.35*np.clip(u/.04,0,1)
 out['T_Trail02']=(1-v)**3*np.clip(v/.03,0,1)  # clean gradient band without streaks
 # Static alpha gradient for columns; the scrolling streaks come from T_NoiseStreak02.
 out['T_GradientV01']=v**1.6*np.clip((1-v)/.03,0,1)  # procedural mesh V runs top->base: solid at the base, gone at the top
 # Beam cross-section: soft Gaussian across U, constant along V, so a sprite stretched along V keeps full strength
 # from end to end (a radial glow stretched into a beam pinches at both ends).
 out['T_BeamSection01']=np.exp(-(x/.42)**2)*np.clip((1-np.abs(x))/.08,0,1)
 # Polar patterns: ground shockwave with radial streaks, and thin speed lines for impacts.
 polar=np.random.default_rng(71).random(96)**2
 spokes=np.interp((angle+np.pi)/(2*np.pi)*96,np.arange(97),np.append(polar,polar[0]))
 out['T_Shockwave01']=np.clip((r-.3)/.5,0,1)**2*np.clip((.94-r)/.05,0,1)*(.35+.65*spokes)
 lines=np.random.default_rng(83).random(180); thin=(lines>.8)*lines
 rays=np.interp((angle+np.pi)/(2*np.pi)*180,np.arange(181),np.append(thin,thin[0]))
 reach=.45+.5*np.interp((angle+np.pi)/(2*np.pi)*180,np.arange(181),np.append(lines,lines[0])[::-1])
 out['T_SpeedLines01']=np.clip(rays*np.clip((r-.16)/.1,0,1)*np.clip((reach-r)/.3,0,1)*1.6,0,1)
 return out

def procedural(n=256,root=None,missing_only=False):
 """Write the math textures to textures/procedural and textures/processed. `missing_only` (what init uses) never
 replaces a file that exists, so a project's edited copy survives; the `procedural` command regenerates all."""
 base=Path(root) if root else ROOT  # the workspace being initialised, which need not be the process's project
 for folder in ['procedural','processed']:(base/f'vfx/textures/{folder}').mkdir(parents=True,exist_ok=True)
 def save(name,image):
  for folder in ['procedural','processed']:
   target=base/f'vfx/textures/{folder}/{name}.png'
   if missing_only and (target.exists() or target.is_symlink()):continue
   image.save(guard(target,base/'vfx'))
 names=[]
 for name,a in masks(n).items():
  im=Image.new('RGBA',(n,n),(255,255,255,0)); im.putalpha(Image.fromarray((np.clip(a,0,1)*255).astype(np.uint8)))
  save(name,im); names.append(name)
 # Legacy soft-edged noise sprite.
 soft=spectral(n,1.6,seed=3)*np.clip(1-np.hypot(*np.mgrid[-1:1:complex(n),-1:1:complex(n)]),0,1)
 im=Image.new('RGBA',(n,n),(255,255,255,0)); im.putalpha(Image.fromarray((soft*255).astype(np.uint8))); save('T_Noise01',im); names.append('T_Noise01')
 # UV distortion maps are opaque: R/G hold two independent offset fields centred on 0.5.
 for name,beta,seeds in [('T_Distort01',1.8,(101,102)),('T_Distort02',1.2,(103,104))]:
  rgb=np.stack([spectral(n,beta,seed=seeds[0]),spectral(n,beta,seed=seeds[1]),np.full((n,n),.5)],-1)
  save(name,Image.fromarray((rgb*255).astype(np.uint8),'RGB').convert('RGBA')); names.append(name)
 # Screen-space (BackDistortion) maps: RG is the refraction offset around 0.5, alpha masks where it applies.
 y,x=np.mgrid[-1:1:complex(n),-1:1:complex(n)]; r=np.sqrt(x*x+y*y)+1e-6
 band=np.exp(-((r-.7)/.13)**2)*(r<.98)                       # shockwave: radial push concentrated in a ring
 ring=np.stack([.5+.5*x/r*band,.5+.5*y/r*band,np.full((n,n),.5),np.clip(band*1.4,0,1)],-1)
 save('T_DistortRing01',Image.fromarray((ring*255).astype(np.uint8),'RGBA')); names.append('T_DistortRing01')
 soft=np.clip(1-r,0,1)**1.2                                    # heat haze: turbulent offsets in a soft disc
 haze=np.stack([spectral(n,1.6,seed=107),spectral(n,1.6,seed=108),np.full((n,n),.5),soft],-1)
 save('T_DistortHaze01',Image.fromarray((haze*255).astype(np.uint8),'RGBA')); names.append('T_DistortHaze01')
 cross=Image.new('RGBA',(128,128),(255,255,255,0)); draw=ImageDraw.Draw(cross)
 draw.rounded_rectangle((54,20,74,108),radius=3,fill='white'); draw.rounded_rectangle((20,54,108,74),radius=3,fill='white')
 save('T_Cross01',cross); names.append('T_Cross01')
 return names
def inspect(path,threshold=8):
 """Measure a texture so recipes can use numbers instead of eyeballed magic constants.

 Angles are degrees counter-clockwise from +x with y up, the same convention as sprite Z rotation.
 bulge_deg points from the bounding-box centre toward the alpha-weighted centroid: for a crescent that is
 the side the arc bows out to. touches_border means the shape is probably clipped by the canvas.
 """
 image=Image.open(path); size=image.size
 a=np.asarray(image.convert('RGBA'),dtype=np.float64)
 alpha=a[...,3]/255 if a[...,3].min()<255 else a[...,:3].mean(axis=2)/255  # opaque maps: read luminance
 mask=alpha>threshold/255; h,w=alpha.shape
 info={'name':Path(path).stem,'size':list(size),'coverage':round(float(mask.mean()),4),'opaque':bool(a[...,3].min()==255)}
 # Seam ratio <= ~1.5 means the opposite edges continue each other, i.e. the map tiles.
 inner=(np.abs(np.diff(alpha,axis=1)).mean()+np.abs(np.diff(alpha,axis=0)).mean())/2
 seam=(np.abs(alpha[:,0]-alpha[:,-1]).mean()+np.abs(alpha[0]-alpha[-1]).mean())/2
 info['seam_ratio']=round(float(seam/inner),2) if inner>0 else None
 if not mask.any():return info|{'empty':True}
 ys,xs=np.nonzero(mask)
 info['bbox']=[round(xs.min()/w,3),round(ys.min()/h,3),round((xs.max()+1)/w,3),round((ys.max()+1)/h,3)]
 edge=max(1,round(min(h,w)*.01))
 info['touches_border']=bool(mask[:edge].any() or mask[-edge:].any() or mask[:,:edge].any() or mask[:,-edge:].any())
 weight=alpha*mask; total=weight.sum(); yy,xx=np.mgrid[0:h,0:w]
 cx=(weight*xx).sum()/total; cy=(weight*yy).sum()/total
 info['centroid']=[round(cx/w,3),round(1-cy/h,3)]  # y up
 dx=xx-cx; dy=-(yy-cy)
 cov=np.array([[(weight*dx*dx).sum(),(weight*dx*dy).sum()],[(weight*dx*dy).sum(),(weight*dy*dy).sum()]])/total
 values,vectors=np.linalg.eigh(cov); major=vectors[:,1]
 info['orientation_deg']=round(float(np.degrees(np.arctan2(major[1],major[0]))%180),1)
 info['elongation']=round(float(np.sqrt(values[1]/max(values[0],1e-9))),2)
 bx=(xs.min()+xs.max()+1)/2; by=(ys.min()+ys.max()+1)/2; ox,oy=cx-bx,-(cy-by)
 info['bulge_deg']=round(float(np.degrees(np.arctan2(oy,ox))%360),1) if np.hypot(ox,oy)>min(h,w)*.01 else None
 return info

def inspect_all(folder=None):
 return {path.stem:inspect(path) for path in sorted(Path(folder or ROOT/'vfx/textures/processed').glob('*.png'))}

