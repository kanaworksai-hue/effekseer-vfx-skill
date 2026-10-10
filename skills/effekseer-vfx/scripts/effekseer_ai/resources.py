"""Preserve original generated masks and produce straight-alpha power-of-two sprites."""
from pathlib import Path
from PIL import Image, ImageOps

def process_texture(source: str, output: str, size: int=256, threshold: int=8, padding: float=.08, mask: bool=True, grid: tuple|None=None) -> dict:
 src,dst=Path(source).resolve(),Path(output).resolve()
 if src==dst: raise ValueError('Output cannot overwrite the original image')
 if not src.is_file(): raise FileNotFoundError(src)
 if size<64 or size>2048 or size & (size-1): raise ValueError('Size must be a power of two between 64 and 2048')
 if not 0<=threshold<255 or not 0<=padding<.45: raise ValueError('Invalid threshold or padding')
 im=Image.open(src).convert('RGBA')
 if mask:
  alpha=ImageOps.grayscale(im).point(lambda x:round(max(0,x-threshold)*255/(255-threshold)))
  from PIL import ImageChops
  alpha=ImageChops.multiply(alpha,im.getchannel('A'))
  im=Image.new('RGBA',im.size,(255,255,255,0)); im.putalpha(alpha)
 if grid:
  # Flipbook sheet: keep every cell where it is (re-centring frames would make the animation jitter) and
  # feather each cell's border so neighbouring frames never bleed in under bilinear filtering.
  import numpy as np
  cols,rows=grid; im=im.resize((size,size),Image.Resampling.LANCZOS)
  cw,ch=size//cols,size//rows; edge=max(2,cw//32)
  wx=np.clip(np.minimum(np.arange(cw),cw-1-np.arange(cw))/edge,0,1); wy=np.clip(np.minimum(np.arange(ch),ch-1-np.arange(ch))/edge,0,1)
  window=np.tile(np.outer(wy,wx),(rows,cols))
  alpha=np.asarray(im.getchannel('A')).astype(float)*window
  im.putalpha(Image.fromarray(alpha.round().astype(np.uint8)))
  dst.parent.mkdir(parents=True,exist_ok=True); im.save(dst)
  return {'source':str(src),'output':str(dst),'size':size,'grid':list(grid),'alpha':'straight','visible_pixels':sum(im.getchannel('A').histogram()[9:])}
 bbox=im.getchannel('A').point(lambda v:255 if v>12 else 0).getbbox()
 if not bbox: raise ValueError('Source has no visible effect pixels')
 im=im.crop(bbox); usable=round(size*(1-2*padding))
 im.thumbnail((usable,usable),Image.Resampling.LANCZOS)
 result=Image.new('RGBA',(size,size),(255,255,255,0))
 result.alpha_composite(im,((size-im.width)//2,(size-im.height)//2))
 dst.parent.mkdir(parents=True,exist_ok=True);result.save(dst)
 return {'source':str(src),'output':str(dst),'size':size,'crop':list(bbox),'alpha':'straight','visible_pixels':sum(result.getchannel('A').histogram()[9:])}
