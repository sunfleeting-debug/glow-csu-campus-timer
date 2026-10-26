"""Read-only photographic re-shoot of v19. Never saves or exports the source model.
Camera/studio objects and exploded poses exist only in this Python process.
"""
from pathlib import Path
import sys,json,hashlib,textwrap,math,argparse
from project_config import ROOT,SOURCE,OUT,configure_cycles
import bpy
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
from PIL import Image,ImageDraw,ImageFont
CACHE=OUT/'_render_cache';OUT.mkdir(parents=True,exist_ok=True);CACHE.mkdir(exist_ok=True)
RENDERABLE={'MESH','CURVE','FONT','SURFACE','META','CURVES','VOLUME','POINTCLOUD','GREASEPENCIL','GPENCIL'}
LABELS={'gate':'复刻校门与浅浮雕','landscape':'校园建筑与园景','platform':'承托平台与铺地','housing':'固定上壳与导光环','led_ring':'环形 LED 灯板','main_pcb':'灯光控制主板','carrier':'安装托架与固定支柱','rotor':'360°旋转计时底座','bottom':'底盖与防滑脚'}

def prepare():
 bpy.ops.wm.open_mainfile(filepath=str(SOURCE));sc=bpy.context.scene;sc.frame_set(1);bpy.context.view_layer.update()
 from component_groups import group_components
 keys,groups,geometry,skipped=group_components(bpy,Vector)
 # All curves and text are isolated with their owning component; no mesh-only mask.
 allgeo=[o for o in bpy.data.objects if o.type in RENDERABLE]
 original={o:(o.matrix_world.copy(),o.data.as_pointer()) for o in allgeo}
 for o in allgeo:o.hide_render=True
 for o in bpy.data.objects:
  if o.type=='LIGHT':o.hide_render=True
 studio=bpy.data.collections['00_STUDIO']
 me=bpy.data.meshes.new('PHOTO19 temporary floor');me.from_pydata([(-3,-3,0),(3,-3,0),(3,3,0),(-3,3,0)],[],[(0,1,2,3)]);me.update();floor=bpy.data.objects.new('PHOTO19 temporary shadow floor',me);studio.objects.link(floor);floor.is_shadow_catcher=True
 mat=bpy.data.materials.new('PHOTO19 studio receiver');mat.use_nodes=True;mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.72,.72,.68,1);mat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.8;me.materials.append(mat)
 lights=[]
 for name,delta,power,size,color in [
  ('large warm key',(-.30,-.36,.46),26,.32,(1,.94,.86)),
  ('cool soft fill',(.33,-.18,.24),10,.40,(.84,.91,1)),
  ('edge softbox',(.20,.30,.43),31,.25,(1,.98,.91)),
  ('top diffusion',(-.08,.07,.50),9,.32,(1,1,1))]:
  d=bpy.data.lights.new('PHOTO19 '+name,'AREA');d.energy=power;d.shape='DISK';d.size=size;d.color=color;o=bpy.data.objects.new('PHOTO19 '+name,d);studio.objects.link(o);lights.append((o,Vector(delta)))
 sc.world.use_nodes=True;sc.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.82,.86,.89,1);sc.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.14
 sc.view_settings.view_transform='AgX';sc.view_settings.exposure=-1.35;sc.view_settings.gamma=1
 try:sc.view_settings.look='AgX - Medium High Contrast'
 except Exception:pass
 d=bpy.data.cameras.new('PHOTO19 independent photographic camera');cam=bpy.data.objects.new('PHOTO19 camera',d);studio.objects.link(cam);d.type='ORTHO';d.sensor_fit='HORIZONTAL';d.clip_start=.001;d.clip_end=100
 sc.camera=cam;sc.render.engine='CYCLES';sc.cycles.use_denoising=True;sc.render.resolution_percentage=100;sc.render.image_settings.file_format='PNG';sc.render.image_settings.color_mode='RGBA';sc.render.film_transparent=True
 configure_cycles(sc)
 return {'sc':sc,'groups':groups,'keys':keys,'allgeo':allgeo,'original':original,'floor':floor,'lights':lights,'cam':cam,'records':{}}

def bbox(obs):
 pts=[o.matrix_world@Vector(c) for o in obs for c in o.bound_box];lo=Vector(tuple(min(p[i] for p in pts) for i in range(3)));hi=Vector(tuple(max(p[i] for p in pts) for i in range(3)));return pts,lo,hi

def shoot(ctx,name,objs,offset=(.22,-.85,.38),size=(2000,1800),samples=48,part=False,under=False,focus=None,scale=None):
 sc,cam=ctx['sc'],ctx['cam'];obs=set(objs)
 for o in ctx['allgeo']:o.hide_render=o not in obs
 pts,lo,hi=bbox(objs);centre=(lo+hi)*.5;vec=Vector(offset);quat=(-vec).to_track_quat('-Z','Y');basis=quat.to_matrix();right=basis@Vector((1,0,0));up=basis@Vector((0,1,0));xs=[p.dot(right) for p in pts];ys=[p.dot(up) for p in pts]
 if focus is None:centre+=right*((min(xs)+max(xs))*.5-centre.dot(right))+up*((min(ys)+max(ys))*.5-centre.dot(up))
 else:centre=Vector(focus)
 W,H=size;sc.render.resolution_x=W;sc.render.resolution_y=H;sc.cycles.samples=samples;cam.data.ortho_scale=scale or max((max(xs)-min(xs))/.86,(max(ys)-min(ys))*(W/H)/.84);cam.location=centre+vec.normalized()*.95;cam.rotation_euler=quat.to_euler();ctx['floor'].hide_render=under;ctx['floor'].location.z=lo.z-.00012
 for light,delta in ctx['lights']:
  dv=delta.copy();az=math.atan2(vec.x,-vec.y);xx,yy=dv.x,dv.y;dv.x=xx*math.cos(az)-yy*math.sin(az);dv.y=xx*math.sin(az)+yy*math.cos(az)
  if under:dv.z=-abs(dv.z)
  light.location=centre+dv;light.rotation_euler=(centre-light.location).to_track_quat('-Z','Y').to_euler()
 bpy.context.view_layer.update();screen=[world_to_camera_view(sc,cam,p) for p in pts];rect=[min(p.x for p in screen)*W,min((1-p.y)*H for p in screen),max(p.x for p in screen)*W,max((1-p.y)*H for p in screen)]
 if scale is None:assert rect[0]>=35 and rect[1]>=35 and rect[2]<=W-35 and rect[3]<=H-35,(name,rect)
 raw=CACHE/(name+'.png');sc.render.filepath=str(raw);bpy.ops.render.render(write_still=True)
 with Image.open(raw) as src:
  rgba=src.convert('RGBA');im=Image.new('RGB',src.size,(246,244,238));im.paste(rgba,(0,0),rgba.getchannel('A'))
 dest=(OUT/'分解大图') if part else OUT;dest.mkdir(exist_ok=True);path=dest/(name+'.png');im.save(path)
 visible={o.name for o in ctx['allgeo'] if not o.hide_render};assert visible=={o.name for o in objs}
 ctx['records'][name]={'image':str(path),'resolution':[W,H],'model_projected_bbox_px':rect,'visible_component_objects':len(objs),'visible_names':sorted(visible),'camera_ortho_width_m':cam.data.ortho_scale,'independent_studio_lights':4,'underside_lighting':under,'source_geometry_modified':False}
 print('PHOTO_COMPLETE',name,flush=True);return path

def unchanged(ctx):
 for o,(world,data) in ctx['original'].items():
  assert o.data.as_pointer()==data,o.name
  assert max(abs(o.matrix_world[i][j]-world[i][j]) for i in range(4) for j in range(4))<1e-8,o.name
 return True

def main():
 p=argparse.ArgumentParser();p.add_argument('--mode',choices=['preview','parts','views','electronics','bottom'],default='preview');a=p.parse_args();ctx=prepare();g=ctx['groups'];allprod=list({o for obs in g.values() for o in obs});harness=[o for o in ctx['allgeo'] if o.get('electronic_role')=='harness'];full=allprod+harness
 if a.mode=='preview':
  shoot(ctx,'预览_整机',full,(.23,-.85,.31),(1000,1100),32)
  shoot(ctx,'预览_复刻校门',g['gate'],(.18,-.80,.20),(1100,1000),32)
  shoot(ctx,'预览_主板',g['main_pcb'],(.21,-.75,.72),(1100,950),32)
 elif a.mode=='parts':
  for i,key in enumerate(ctx['keys'],1):
   under=False;angle=(.19,-.80,.57) if key=='bottom' else (.18,-.80,.22 if key=='gate' else .49 if key=='landscape' else .70)
   shoot(ctx,'%02d_%s_光影版'%(i,LABELS[key]),g[key],angle,(1800,1550),48,True,under)
 elif a.mode=='bottom':
  shoot(ctx,'09_底盖与防滑脚_光影版',g['bottom'],(.19,-.80,.57),(1800,1550),48,True,False)
  path=OUT/'拍摄数据_parts.json'
  if path.exists():
   part_report=json.loads(path.read_text(encoding='utf-8'));part_report['images'].update(ctx['records']);path.write_text(json.dumps(part_report,ensure_ascii=False,indent=2),encoding='utf-8')
 elif a.mode=='views':
  for name,angle,size in [('整体效果图_光影版',(.23,-.85,.31),(2200,2400)),('正视图_光影版',(0,-.85,.10),(2200,2400)),('背面效果图_光影版',(-.24,.85,.33),(2200,2400)),('侧视图_光影版',(.85,-.12,.25),(2200,2400)),('俯视图_光影版',(0,-.01,1),(2200,2200))]:shoot(ctx,name,full,angle,size,56)
  for name,angle,focus,scale in [('左侧校训_光影版',(-.85,-.06,.13),(-.080,0,.046),.155),('右侧校训_光影版',(.85,-.06,.13),(.080,0,.046),.155),('背面矿业湘雅_光影版',(.10,.85,.13),(0,.080,.045),.16),('360度刻度_光影版',(.08,-.85,.15),(0,-.080,.021),.155)]:shoot(ctx,name,full,angle,(2200,1200),56,focus=focus,scale=scale)
  cap=[o for o in g['gate'] if ('右'in o.name and any(t in o.name for t in ['柱头','束带','平板','上柱','侧面板','卷草带']))]
  shoot(ctx,'复刻校门雕刻特写_光影版',g['gate'],(.20,-.80,.15),(2200,1700),64,focus=bbox(cap)[1].lerp(bbox(cap)[2],.5),scale=.050)
 elif a.mode=='electronics':
  internal=[o for o in ctx['allgeo'] if o.get('electronic_role') in ['main_pcb','led_ring','carrier','harness']]
  shoot(ctx,'电子结构装配_光影版',internal,(.26,-.80,.66),(2200,1900),56)
  shoot(ctx,'灯光控制主板特写_光影版',g['main_pcb'],(.20,-.75,.72),(2200,1800),64)
  shoot(ctx,'环形LED灯板特写_光影版',g['led_ring'],(.20,-.75,.78),(2200,1900),56)
  shoot(ctx,'固定线束接口_光影版',internal,(.05,-.10,1),(2200,2200),56)
 unchanged(ctx)
 report={'source':str(SOURCE),'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'mode':a.mode,'source_geometry_and_world_transforms_unchanged':True,'source_file_not_saved':True,'isolation_includes':['MESH','CURVE','FONT','SURFACE','META','CURVES','VOLUME','POINTCLOUD'],'all_group_counts':{k:len(v) for k,v in g.items()},'images':ctx['records']}
 (OUT/('拍摄数据_'+a.mode+'.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print('V19_PHOTOGRAPHY_COMPLETE',a.mode,flush=True)
if __name__=='__main__':main()
