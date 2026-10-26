"""Read-only two-column v19 exploded display, using unmodified real geometry.

python scripts/explode_v19_photography.py --dry-run   # CPU layout/group audit; no GPU
python scripts/explode_v19_photography.py             # two transparent renders, after GPU handoff
"""
from pathlib import Path
import sys,argparse,ast,json,math,hashlib
from project_config import ROOT,SOURCE,OUT,configure_cycles,get_font

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dry-run',action='store_true');p.add_argument('--samples',type=int,default=28);p.add_argument('--source',type=Path,default=SOURCE);p.add_argument('--no-pcb-inset',action='store_true');args=p.parse_args()
 source=args.source.resolve()
 if not source.is_file():raise FileNotFoundError(source)
 import bpy,numpy as np
 from mathutils import Vector,Matrix
 from bpy_extras.object_utils import world_to_camera_view
 from PIL import Image,ImageDraw,ImageFont
 OUT.mkdir(parents=True,exist_ok=True);CACHE=OUT/'_explode_cache';CACHE.mkdir(exist_ok=True)
 bpy.ops.wm.open_mainfile(filepath=str(source));sc=bpy.context.scene;sc.frame_set(1);bpy.context.view_layer.update()
 # Reuse the proven nine-layer classification, with no old rendering or file
 # output statements executed. The extracted block ends before 'originals'.
 from component_groups import group_components
 keys,groups,geometry,skipped=group_components(bpy,Vector)
 originals={o:o.matrix_world.copy() for obs in groups.values() for o in obs};signatures={o:(o.data.as_pointer(),len(o.data.vertices) if o.type=='MESH' else None,len(o.data.polygons) if o.type=='MESH' else None) for o in originals}
 # Local vertex arrays give accurate circular-board extents: square bounding
 # boxes would make round parts look smaller than the reported fit.
 cache={}
 for o,m in originals.items():
  if o.type=='MESH':
   v=np.empty(len(o.data.vertices)*3,dtype=np.float32);o.data.vertices.foreach_get('co',v);cache[o]=(v.reshape(-1,3),np.array(m,dtype=float),False)
  else:cache[o]=(np.array([tuple(m@Vector(c)) for c in o.bound_box],dtype=float),None,True)
 def range_on(obs,axis):
  aa=np.array(axis,dtype=float);lo=1e9;hi=-1e9
  for o in obs:
   v,m,world=cache[o]
   if not len(v):continue
   value=v@aa if world else v@(m[:3,:3].T@aa)+float(m[:3,3]@aa);lo=min(lo,float(value.min()));hi=max(hi,float(value.max()))
  return lo,hi
 W,H=3600,2800;MARGIN=72;GUTTER=80;CW=(W-2*MARGIN-GUTTER)//2;CH=2400;Y0=245;TOPPAD=66;BOTPAD=18
 columns=[{'id':'left','keys':['gate','landscape','platform','housing'],'x':MARGIN,'title':'01—04  外观总成','angles':[23,21,19,17,15,13]}, {'id':'right','keys':['led_ring','main_pcb','carrier','rotor','bottom'],'x':MARGIN+CW+GUTTER,'title':'05—09  灯光与计时','angles':[28,26,24,22,20]}]
 plans=[];records={}
 for col in columns:
  selected=None
  for down in col['angles']:
   az=math.radians(12 if col['id']=='left' else 18);dd=math.radians(down);offset=Vector((math.sin(az)*math.cos(dd),-math.cos(az)*math.cos(dd),math.sin(dd)));rot=(-offset).to_track_quat('-Z','Y');basis=rot.to_matrix();right=basis@Vector((1,0,0));up=basis@Vector((0,1,0));shifts={};projected={};previous=None;gap=.0075
   for key in reversed(col['keys']):
    lo,hi=range_on(groups[key],up);dz=0. if previous is None else max(0.,(previous+gap-lo)/up.z);shifts[key]=Vector((0,0,dz));projected[key]=[lo+dz*up.z,hi+dz*up.z];previous=projected[key][1]
   xlo=min(range_on(groups[k],right)[0] for k in col['keys']);xhi=max(range_on(groups[k],right)[1] for k in col['keys']);ylo=min(v[0] for v in projected.values());yhi=max(v[1] for v in projected.values());ppm=min((CH-TOPPAD-BOTPAD)/(yhi-ylo),(CW-80)/(xhi-xlo));occupancy=(xhi-xlo)*ppm/CW
   selected={'id':col['id'],'keys':col['keys'],'x':col['x'],'title':col['title'],'angle_down_deg':down,'offset':offset,'rotation':rot,'right':right,'up':up,'shifts':shifts,'projected_up':projected,'xspan':[xlo,xhi],'yspan':[ylo,yhi],'pixels_per_metre':ppm,'actual_entity_width_px':(xhi-xlo)*ppm,'column_width_px':CW,'actual_entity_width_fraction':occupancy,'ortho_width_m':CW/ppm}
   if occupancy>=.575:break
  if selected['actual_entity_width_fraction']<.55:raise RuntimeError('Tight two-column fit still below 55 percent occupied width: '+str(selected['actual_entity_width_fraction']))
  plans.append(selected)
  for key in col['keys']:
   delta=selected['shifts'][key];records[key]={'geometry_objects':len(groups[key]),'objects':[o.name for o in groups[key]],'column':col['id'],'translation_world_mm':list(delta*1000),'projected_up_interval_m':selected['projected_up'][key]}
 # Save original world transforms once, remove only in-memory transform
 # animation/constraints, and never transform a geometry parent twice.
 for o in originals:
  o.parent=None
  if o.animation_data:o.animation_data_clear()
  for c in o.constraints:c.mute=True
  o.matrix_world=originals[o]
 studio=bpy.data.collections['00_STUDIO'];info={};cameras={}
 for plan in plans:
  for k in plan['keys']:
   for o in groups[k]:o.matrix_world=Matrix.Translation(plan['shifts'][k])@originals[o]
  bpy.context.view_layer.update();ppm=plan['pixels_per_metre'];cx=sum(plan['xspan'])*.5;cy=sum(plan['yspan'])*.5;desiredY=(TOPPAD+CH-BOTPAD)*.5;camY=cy+(desiredY-CH*.5)/ppm;zmid=sum((o.matrix_world.translation.z for k in plan['keys'] for o in groups[k]))/sum(len(groups[k]) for k in plan['keys']);target=Vector((0,0,zmid));target+=plan['right']*(cx-target.dot(plan['right']))+plan['up']*(camY-target.dot(plan['up']))
  d=bpy.data.cameras.new('V18 large '+plan['id']);cam=bpy.data.objects.new('EXPLODE_V18_LARGE | '+plan['id'],d);studio.objects.link(cam);cam.location=target+plan['offset']*2.;cam.rotation_euler=plan['rotation'].to_euler();d.type='ORTHO';d.sensor_fit='HORIZONTAL';d.ortho_scale=plan['ortho_width_m'];d.clip_start=.001;d.clip_end=100;cameras[plan['id']]=cam;sc.camera=cam;sc.render.resolution_x=CW;sc.render.resolution_y=CH;sc.render.resolution_percentage=100
  for key in plan['keys']:
   obs=groups[key];rightRange=range_on(obs,plan['right']);upRange=plan['projected_up'][key];xc0=CW*.5+(rightRange[0]-cx)*ppm;xc1=CW*.5+(rightRange[1]-cx)*ppm;yc0=CH*.5-(upRange[1]-camY)*ppm;yc1=CH*.5-(upRange[0]-camY)*ppm;info[key]={'bbox_px':[xc0,yc0,xc1,yc1],'label_y':yc0-37,'column':plan['id']};records[key]['column_screen_bbox_px']=info[key]['bbox_px'];records[key]['label_position_px']=[plan['x']+xc0,Y0+yc0-37]
  plan['zmid']=(min((o.matrix_world@Vector(c)).z for k in plan['keys'] for o in groups[k] for c in o.bound_box)+max((o.matrix_world@Vector(c)).z for k in plan['keys'] for o in groups[k] for c in o.bound_box))*.5
 serial=[]
 for p in plans:serial.append({k:v for k,v in p.items() if k not in {'offset','rotation','right','up','shifts'}})
 metadata={'source':str(source),'layer_order_top_to_bottom':keys,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'groups':{k:records[k] for k in keys},'column_plans':serial,'page_resolution':[W,H],'transparent_column_resolution':[CW,CH],'frame_frozen':1,'same_scale_within_each_column':True,'groups_internally_unscaled':True,'only_world_translations':True,'world_transform_applied_once_per_renderable':True,'model_geometry_unchanged':True,'source_file_not_modified':True,'old_vertical_outputs_untouched':True,'excluded':skipped,'rendered':False,'pcb_local_inset':{'enabled':not args.no_pcb_inset,'method':'marked crop enlargement of the genuine rendered PCB centre, if adjacent white space permits; no extra/model geometry is invented'}}
 new_json=OUT/'爆炸图拍摄数据.json';new_json.write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8')
 print('LARGE_DRY_LAYOUT',json.dumps({'resolution':[W,H],'columns':[{k:p[k] for k in ['id','keys','angle_down_deg','actual_entity_width_px','column_width_px','actual_entity_width_fraction']} for p in plans],'group_counts':{k:len(groups[k]) for k in keys}},ensure_ascii=False),flush=True)
 if args.dry_run:print('LARGE_DRY_RUN_COMPLETE_NO_GPU',flush=True);return
 # No GPU is touched before this point. Run only after the root's handoff.
 for ob in bpy.data.objects:
  if ob.type=='LIGHT':ob.hide_render=True
 world=sc.world;world.use_nodes=True;bg=world.node_tree.nodes.get('Background');bg.inputs['Color'].default_value=(.82,.86,.89,1);bg.inputs['Strength'].default_value=.18
 sc.view_settings.view_transform='AgX';sc.view_settings.exposure=-2.0;sc.view_settings.gamma=1
 try:sc.view_settings.look='AgX - Medium High Contrast'
 except Exception:pass
 lights=[]
 for name,xyz,power,size in [('key',(-.42,-.66,.20),80,.85),('fill',(.50,-.46,.05),22,.90),('rim',(.10,.48,.23),75,.70)]:
  ld=bpy.data.lights.new('V18 LARGE '+name,'AREA');ld.energy=power;ld.shape='DISK';ld.size=size;ob=bpy.data.objects.new('V18 LARGE '+name,ld);studio.objects.link(ob);lights.append((ob,xyz))
 sc.render.engine='CYCLES';sc.render.image_settings.file_format='PNG';sc.render.image_settings.color_mode='RGBA';sc.render.film_transparent=True;sc.cycles.samples=max(8,args.samples);sc.cycles.use_denoising=True
 configure_cycles(sc)
 for plan in plans:
  for o in bpy.data.objects:
   if o.type in geometry:o.hide_render=True
  obs=[o for k in plan['keys'] for o in groups[k]]
  for o in obs:o.hide_render=False
  for floor in studio.objects:
   if floor.type=='MESH' and ('floor' in floor.name.lower() or 'ground' in floor.name.lower()):floor.hide_render=True;floor.is_shadow_catcher=True
  for light,xyz in lights:light.location=(xyz[0],xyz[1],xyz[2]+plan['zmid']);light.rotation_euler=(Vector((0,0,plan['zmid']))-light.location).to_track_quat('-Z','Y').to_euler()
  sc.camera=cameras[plan['id']];sc.render.resolution_x=CW;sc.render.resolution_y=CH;sc.render.filepath=str(CACHE/('column_'+plan['id']+'.png'));bpy.ops.render.render(write_still=True);print('LARGE_COLUMN_RENDERED',plan['id'],flush=True)
 if any((o.data.as_pointer(),len(o.data.vertices) if o.type=='MESH' else None,len(o.data.polygons) if o.type=='MESH' else None)!=v for o,v in signatures.items()):raise RuntimeError('Model mesh changed unexpectedly')
 page=Image.new('RGB',(W,H),(248,246,241));draw=ImageDraw.Draw(page);font=get_font();title=ImageFont.truetype(font,62);sub=ImageFont.truetype(font,29);section=ImageFont.truetype(font,34);label=ImageFont.truetype(font,31);number=ImageFont.truetype(font,25);small=ImageFont.truetype(font,23)
 draw.text((72,35),'逐光中南 v19｜光影拆解展示',font=title,fill=(57,47,39));draw.text((74,119),'真实模型摄影 · 双栏放大展示 · 结构组内比例保持一致',font=sub,fill=(111,99,84));draw.line([(W//2,222),(W//2,H-117)],fill=(220,213,202),width=2)
 labels={'gate':'复刻校门与浅浮雕','landscape':'校园建筑与园景','platform':'承托平台与铺地','housing':'固定上壳与导光环','led_ring':'环形 LED 灯板','main_pcb':'灯光控制主板','carrier':'安装托架与固定支柱','rotor':'全圈旋转刻度底座','bottom':'底盖与防滑脚'}
 for plan in plans:
  x=plan['x'];accent=(80,100,76) if plan['id']=='right' else (93,76,58);draw.text((x,182),plan['title'],font=section,fill=accent)
  # Dashed guide stays behind the real rendered geometry, never across a PCB.
  axisX=x+CW//2
  for y in range(Y0+50,Y0+CH-12,30):draw.line([(axisX,y),(axisX,y+11)],fill=(185,171,153),width=2)
  with Image.open(CACHE/('column_'+plan['id']+'.png')) as im:tile=im.convert('RGBA')
  page.paste(tile,(x,Y0),tile.getchannel('A'));draw=ImageDraw.Draw(page)
  for key in plan['keys']:
   n=keys.index(key)+1;xx,yy,_,_=info[key]['bbox_px'];ly=Y0+info[key]['label_y'];lx=x+max(28,min(CW-500,xx));draw.ellipse((lx-31,ly+1,lx+1,ly+33),fill=(248,246,241),outline=accent,width=2);text=str(n);bb=draw.textbbox((0,0),text,font=number);draw.text((lx-15-(bb[2]-bb[0])/2,ly),text,font=number,fill=accent);draw.text((lx+12,ly-2),labels[key],font=label,fill=accent)
  if plan['id']=='right' and not args.no_pcb_inset:
   x0,y0,x1,y1=info['main_pcb']['bbox_px'];bw=x1-x0;bh=y1-y0;crop=(int(x0+bw*.27),int(y0+bh*.16),int(x0+bw*.68),int(y0+bh*.84));cw=crop[2]-crop[0];ch=crop[3]-crop[1];gapRight=CW-x1-25
   slotTop=info['led_ring']['bbox_px'][3]+15;slotBottom=info['carrier']['bbox_px'][1]-12;scale=min(1.85,max(0,gapRight-25)/max(1,cw),max(0,slotBottom-slotTop-50)/max(1,ch))
   if scale>=1.25 and cw>5 and ch>5:
    iw=int(cw*scale);ih=int(ch*scale);ix=CW-iw-14;iy=max(slotTop+35,min((y0+y1)*.5-ih*.5,slotBottom-ih));panel=Image.new('RGB',(iw+18,ih+49),(250,248,243));pd=ImageDraw.Draw(panel);pd.rectangle((0,0,iw+17,ih+48),outline=(137,148,124),width=2);pd.text((9,5),'局部放大 ×'+format(scale,'.1f'),font=small,fill=(83,103,76));roi=tile.crop(crop).resize((iw,ih),Image.Resampling.LANCZOS);panel.paste(roi,(9,36),roi.getchannel('A'));page.paste(panel,(x+int(ix)-9,Y0+int(iy)-36));metadata['pcb_local_inset'].update({'added':True,'source_column_crop_px':list(crop),'pixel_scale':scale,'page_rect_px':[x+int(ix)-9,Y0+int(iy)-36,iw+18,ih+49]})
   else:metadata['pcb_local_inset'].update({'added':False,'reason':'Insufficient adjacent white space for a genuine enlargement; full PCB remains visible at the shared column scale'})
 draw=ImageDraw.Draw(page);draw.text((72,H-73),'外观装配分组示意，非制造装配工艺图。',font=sub,fill=(112,98,84));page.save(OUT/'拆解爆炸图_v19_光影双栏.png');metadata['rendered']=True;metadata['image']=str(OUT/'拆解爆炸图_v19_光影双栏.png');new_json.write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8');print('LARGE_TWO_COLUMN_COMPLETE',str(OUT/'拆解爆炸图_v19_光影双栏.png'),flush=True)

if __name__=='__main__':main()
