"""Paths, fonts and render backend; credentials are never needed for rendering."""
from pathlib import Path
import os,sys
ROOT=Path(__file__).resolve().parents[1]
extra=os.environ.get('GLOW_CSU_BPY_PATH')
if extra:sys.path.insert(0,extra)
SOURCE=Path(os.environ.get('GLOW_CSU_MODEL',str(ROOT/'models'/'逐光中南_v19.blend'))).resolve()
OUT=ROOT/'output'/'photos'
def get_font():
 candidates=[os.environ.get('GLOW_CSU_FONT',''),'C:/Windows/Fonts/msyh.ttc','/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc','/System/Library/Fonts/PingFang.ttc']
 for p in candidates:
  if p and Path(p).is_file():return p
 raise FileNotFoundError('Set GLOW_CSU_FONT to a Chinese-capable TTF/TTC font file.')
def configure_cycles(scene):
 import bpy
 mode=os.environ.get('GLOW_CSU_RENDER_DEVICE','auto').lower()
 if mode=='cpu':scene.cycles.device='CPU';return
 try:
  pref=bpy.context.preferences.addons['cycles'].preferences;pref.compute_device_type='CUDA';pref.get_devices()
  available=any(d.type=='CUDA' for d in pref.devices)
  for d in pref.devices:d.use=d.type=='CUDA'
  scene.cycles.device='GPU' if available else 'CPU'
  if mode=='cuda' and not available:raise RuntimeError('CUDA requested but no supported device is available.')
 except Exception:
  if mode=='cuda':raise
  scene.cycles.device='CPU'
