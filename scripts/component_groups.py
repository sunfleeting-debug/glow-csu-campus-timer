"""Group the final scene, including mesh, curve and text components."""
def group_components(bpy, Vector):
 keys=['gate','landscape','platform','housing','led_ring','main_pcb','carrier','rotor','bottom']
 groups={k:[] for k in keys};geometry={'MESH','CURVE','FONT','SURFACE','META'}
 skipped={'old_internal_concept':[],'harness_main_view':[],'hidden_retired_geometry':[],'studio':[]}
 def inherited(ob,field):
  seen=set()
  while ob and ob not in seen:
   seen.add(ob)
   if ob.get(field) is not None:return ob.get(field)
   ob=ob.parent
  return None
 def panel_group(ob):
  for field in ['assembly_group','light_panel_group','panel_group']:
   role=inherited(ob,field)
   if role:
    role=str(role).lower()
    if role in {'gate','portal','arch'}:return 'gate'
    if role in {'platform','paving','path','base_top'}:return 'platform'
    if role in {'landscape','building','campus','windows'}:return 'landscape'
  name=ob.name.lower()
  if any(t in name for t in ['gate','portal','门','arch']):return 'gate'
  if any(t in name for t in ['platform','path','paving','路','平台']):return 'platform'
  return 'landscape'
 for ob in list(bpy.data.objects):
  if ob.type not in geometry:continue
  cols={c.name for c in ob.users_collection};name=ob.name;role=str(inherited(ob,'electronic_role') or '').lower()
  if any(c.startswith('08_') for c in cols):skipped['old_internal_concept'].append(name);continue
  if any(c.startswith('00_') for c in cols):skipped['studio'].append(name);continue
  if role=='harness' or '30_LIGHT_HARNESS_V18' in cols:skipped['harness_main_view'].append(name);continue
  new_electronics=bool(cols&{'28_LIGHT_ELECTRONICS_V18','29_ELECTRONICS_CARRIER_V18','31_LANDSCAPE_LIGHT_PANELS_V18'})
  if ob.hide_render and not new_electronics:skipped['hidden_retired_geometry'].append(name);continue
  if role=='led_ring':group='led_ring'
  elif role=='main_pcb':group='main_pcb'
  elif role=='carrier' or '29_ELECTRONICS_CARRIER_V18' in cols:group='carrier'
  elif '28_LIGHT_ELECTRONICS_V18' in cols:
   # Exact electronic_role is the primary interface; this is only a guard
   # for an untagged individual LED/component in an otherwise tagged model.
   low=name.lower();group='led_ring' if any(t in low for t in ['led','ring','环形']) else 'main_pcb'
  elif '31_LANDSCAPE_LIGHT_PANELS_V18' in cols:group=panel_group(ob)
  elif name.startswith('REAR_V7 | gate reverse') or cols&{'03_GATE_ARCHITECTURE','04_BOTANICAL_RELIEF','10_CSU_CALLIGRAPHIC_INSCRIPTIONS','16_CONCEALED_PORTAL_LIGHT','25_GATE_ARCHITECTURAL_DETAILS'}:group='gate'
  elif '02_TIMER_ROTATING_RING' in cols or '15_TIME_TRACK_DIAL' in cols:group='rotor'
  elif name=='SCENE | ivory platform' or name.startswith(('SCENE | paving','SCENE_V2 | outer inlay','PAVING','UPPER_V16 | thin tapered')):group='platform'
  elif '01_BASE_FIXED' in cols and name.startswith(('BASE | independent bottom cover','BASE | rubber foot','BASE_V2 | recessed screw','BASE_V2 | screw slot')):group='bottom'
  elif cols&{'01_BASE_FIXED','12_JS1953_TRAIN_POINTER','14_BASE_SHALLOW_RELIEF','18_CSU_SIDE_RELIEFS','22_REAR_SCHOLAR_MEMORY_V14','23_TIMER_BEARING_DETAILS'}:group='housing'
  elif '07_LIGHT_ZONES' in cols:
   z=sum((ob.matrix_world@Vector(c)).z for c in ob.bound_box)/8;group='housing' if z<.060 else 'landscape' if name.startswith(('HERITAGE','REAR')) else 'platform'
  else:group='landscape'
  groups[group].append(ob)
 missing=[k for k in keys if not groups[k]]
 if missing:raise RuntimeError('Actual v18 source has empty exploded layers (no placeholder parts are invented): '+', '.join(missing))
 return keys, groups, geometry, skipped
