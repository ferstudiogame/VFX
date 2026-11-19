import bpy, math, json, os, sys, random
from mathutils import Vector
from pathlib import Path

def args():
    a=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
    out=Path("exports"); prev=Path("previews"); ids="all"
    for i,v in enumerate(a):
        if v=="--output": out=Path(a[i+1])
        if v=="--previews": prev=Path(a[i+1])
        if v=="--effects": ids=a[i+1]
    return out.resolve(),prev.resolve(),ids

def clear():
    bpy.ops.object.select_all(action="SELECT"); bpy.ops.object.delete(use_global=False)
    for d in bpy.data.materials: bpy.data.materials.remove(d)

def mat(name,color,emission=0.0,metal=0.0,rough=.3):
    m=bpy.data.materials.new(name); m.diffuse_color=(*color,1); m.use_nodes=True
    p=m.node_tree.nodes.get("Principled BSDF"); p.inputs["Base Color"].default_value=(*color,1)
    p.inputs["Metallic"].default_value=metal; p.inputs["Roughness"].default_value=rough
    p.inputs["Emission Color"].default_value=(*color,1); p.inputs["Emission Strength"].default_value=emission
    return m

def attach(o,root,ma):
    o.parent=root
    if ma and o.type=="MESH": o.data.materials.append(ma)
    return o

def ico(name,loc,scale,ma,root,sub=2):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=sub,radius=1,location=loc)
    o=bpy.context.object; o.name=name; o.scale=scale; return attach(o,root,ma)

def uv(name,loc,scale,ma,root):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=12,radius=1,location=loc)
    o=bpy.context.object; o.name=name; o.scale=scale; return attach(o,root,ma)

def torus(name,loc,major,minor,ma,root,rot=(0,0,0)):
    bpy.ops.mesh.primitive_torus_add(major_radius=major,minor_radius=minor,major_segments=48,minor_segments=8,location=loc,rotation=rot)
    return attach(bpy.context.object,root,ma)

def beam(name,a,b,r,ma,root):
    d=Vector(b)-Vector(a); mid=(Vector(a)+Vector(b))/2
    bpy.ops.mesh.primitive_cylinder_add(vertices=8,radius=r,depth=d.length,location=mid)
    o=bpy.context.object; o.name=name; o.rotation_mode="QUATERNION"; o.rotation_quaternion=d.to_track_quat("Z","Y")
    return attach(o,root,ma)

def cone(name,loc,r1,r2,depth,ma,root,rot=(0,0,0)):
    bpy.ops.mesh.primitive_cone_add(vertices=8,radius1=r1,radius2=r2,depth=depth,location=loc,rotation=rot)
    return attach(bpy.context.object,root,ma)

def curve(name,points,r,ma,root):
    c=bpy.data.curves.new(name,"CURVE"); c.dimensions="3D"; c.bevel_depth=r; c.bevel_resolution=3
    s=c.splines.new("POLY"); s.points.add(len(points)-1)
    for p,co in zip(s.points,points): p.co=(*co,1)
    o=bpy.data.objects.new(name,c); bpy.context.collection.objects.link(o); o.parent=root
    c.materials.append(ma); return o

def setup_scene(root, effect_id, out, previews):
    scene=bpy.context.scene; scene.frame_start=1; scene.frame_end=36; scene.render.engine="BLENDER_EEVEE_NEXT"
    scene.eevee.taa_render_samples=16; scene.render.resolution_x=512; scene.render.resolution_y=512; scene.render.resolution_percentage=100
    scene.render.image_settings.file_format="PNG"; scene.world.color=(.012,.016,.03)
    bpy.ops.object.camera_add(location=(4.8,-7.5,4.5)); cam=bpy.context.object
    cam.rotation_euler=(Vector((0,0,0))-cam.location).to_track_quat("-Z","Y").to_euler(); cam.data.type="ORTHO"; cam.data.ortho_scale=5.2; scene.camera=cam
    bpy.ops.object.light_add(type="AREA",location=(1,-4,5)); key=bpy.context.object; key.data.energy=850; key.data.shape="DISK"; key.data.size=5
    key.rotation_euler=(Vector((0,0,0))-key.location).to_track_quat("-Z","Y").to_euler()
    bpy.ops.object.light_add(type="AREA",location=(-4,1,2)); fill=bpy.context.object; fill.data.energy=450; fill.data.color=(.15,.35,1); fill.data.size=4
    fill.rotation_euler=(Vector((0,0,0))-fill.location).to_track_quat("-Z","Y").to_euler()
    for f,s in [(1,.55),(8,1.0),(24,1.08),(36,.01)]:
        root.scale=(s,s,s); root.keyframe_insert(data_path="scale",frame=f)
    root.rotation_euler=(0,0,0); root.keyframe_insert(data_path="rotation_euler",frame=1)
    root.rotation_euler=(0,0,math.radians(24)); root.keyframe_insert(data_path="rotation_euler",frame=36)
    scene.frame_set(12)
    bpy.context.view_layer.objects.active=root; root.select_set(True)
    for o in bpy.context.selected_objects:
        if o!=root: o.select_set(False)
    out.mkdir(parents=True,exist_ok=True); previews.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(out/(effect_id+".blend")))
    bpy.ops.export_scene.gltf(filepath=str(out/(effect_id+".glb")),export_format="GLB",export_animations=True,export_force_sampling=True,export_frame_range=True,export_apply=True)
    scene.render.filepath=str(previews/(effect_id+".png")); bpy.ops.render.render(write_still=True)
    (out/"manifest.json").write_text(json.dumps({"id":effect_id,"blender":bpy.app.version_string,"source":effect_id+".blend","runtime":"Godot 4 glTF","files":[effect_id+".glb",effect_id+".blend"]},indent=2))
    (out/"INTEGRATION.md").write_text("# "+effect_id+"\n\nCopia este GLB a res://vfx/"+effect_id+"/ y reproduce su clip desde AnimationPlayer.\n")
    return {"id":effect_id,"blend":str(out/(effect_id+".blend")),"glb":str(out/(effect_id+".glb")),"preview":str(previews/(effect_id+".png"))}

def build(eid,out,previews):
    clear(); root=bpy.data.objects.new("VFX_ROOT_"+eid,None); bpy.context.collection.objects.link(root)
    cyan=mat("VFX_Cyan",(0.02,.65,1),7); blue=mat("VFX_Blue",(.025,.12,1),5); white=mat("VFX_White",(.8,.95,1),9)
    orange=mat("VFX_Fire",(1,.12,.008),6); gold=mat("VFX_Gold",(1,.48,.015),4,.55); purple=mat("VFX_Purple",(.38,.025,1),7)
    ice=mat("VFX_Ice",(.22,.8,1),2,.25,.18); dark=mat("VFX_Dark",(.025,.04,.08),.2,.7)
    random.seed(eid)
    if eid=="electric_arc":
        for branch in range(5):
            pts=[]; x=random.uniform(-.25,.25); y=random.uniform(-.2,.2)
            for j in range(7): pts.append((x+random.uniform(-.22,.22),y+j*.09-.27,random.uniform(-.18,.18)))
            curve("Arc_Branch",pts,.025 if branch==0 else .012,white if branch==0 else cyan,root)
        for i in range(8): ico("Spark",(random.uniform(-.7,.7),random.uniform(-.7,.7),random.uniform(-.4,.4)),(.035,)*3,cyan,root,1)
    elif eid=="impact_burst":
        ico("Hot_Core",(0,0,0),(.36,.36,.36),orange,root,2)
        torus("Shockwave",(0,0,0),.75,.045,gold,root)
        for i in range(18):
            a=math.tau*i/18; v=Vector((math.cos(a),math.sin(a),random.uniform(-.35,.35)))
            beam("Debris",(0,0,0),v*.95,.025,gold if i%3 else orange,root)
            ico("Ember",v*.95,(.045,)*3,orange,root,1)
    elif eid=="energy_orb":
        uv("Orb",(0,0,0),(.58,.58,.58),blue,root)
        ico("Core",(0,0,0),(.34,)*3,white,root,3)
        torus("Orbit_A",(0,0,0),.92,.025,cyan,root,(.5,.2,.2))
        torus("Orbit_B",(0,0,0),1.08,.02,purple,root,(1.1,.3,.5))
        for i in range(12):
            a=math.tau*i/12; ico("Orbit_Node",(math.cos(a),math.sin(a),.12*math.sin(a*2)),(.055,)*3,cyan,root,1)
    elif eid=="fireburst":
        ico("Flame_Core",(0,0,0),(.42,.42,.42),orange,root,2)
        for i in range(12):
            a=math.tau*i/12; x=math.cos(a)*.42; y=math.sin(a)*.42
            cone("Flame_Tongue",(x,y,.35),.18,.015,.9,orange if i%2 else gold,root,(math.sin(a)*.5,-math.cos(a)*.5,0))
            ico("Ember",(x*1.5,y*1.5,.7),(.045,)*3,gold,root,1)
        torus("Heat_Ring",(0,0,0),.7,.035,gold,root)
    elif eid=="ice_shatter":
        ico("Frost_Core",(0,0,0),(.3,)*3,ice,root,2)
        for i in range(14):
            a=math.tau*i/14; v=Vector((math.cos(a),math.sin(a),random.uniform(-.5,.5)))
            beam("Ice_Shard",v*.15,v*1.15,.075,ice,root)
            ico("Shard_Tip",v*1.15,(.08,)*3,white,root,1)
        torus("Frost_Ring",(0,0,0),.85,.025,cyan,root)
    elif eid=="portal_gate":
        torus("Portal_Frame",(0,0,0),1.05,.09,dark,root,(math.pi/2,0,0))
        torus("Portal_Energy",(0,0,0),.91,.055,purple,root,(math.pi/2,0,0))
        torus("Portal_Inner",(0,0,0),.72,.025,cyan,root,(math.pi/2,0,0))
        uv("Portal_Core",(0,0,0),(.65,.08,.65),blue,root)
        for i in range(10):
            a=math.tau*i/10; ico("Rune",(math.cos(a),0,math.sin(a)),(.07,)*3,white,root,1)
    elif eid=="plasma_bolt":
        beam("Plasma_Body",(-.95,0,0),(.95,0,0),.19,blue,root)
        beam("Plasma_Core",(-1.05,0,0),(1.05,0,0),.07,white,root)
        for side in [-1,1]:
            for i in range(5):
                x=-.65+i*.32
                curve("Plasma_Trail",[(x,side*.08,0),(x-.2,side*.22,.08),(x-.42,side*.3,0)],.025,cyan,root)
        torus("Plasma_Halo",(0,0,0),.34,.025,purple,root,(0,math.pi/2,0))
    else: raise ValueError("Unknown effect "+eid)
    return setup_scene(root,eid,out,previews)

def main():
    out,prev,selected=args()
    ids=["electric_arc","impact_burst","energy_orb","fireburst","ice_shatter","portal_gate","plasma_bolt"]
    if selected!="all": ids=[x.strip() for x in selected.split(",")]
    bad=set(ids)-{"electric_arc","impact_burst","energy_orb","fireburst","ice_shatter","portal_gate","plasma_bolt"}
    if bad: raise SystemExit("Unknown effects: "+str(sorted(bad)))
    results=[]
    for eid in ids:
        print("GENERATING",eid,flush=True)
        results.append(build(eid,out/eid,prev))
    (out/"build_report.json").write_text(json.dumps({"status":"success","effect_count":len(results),"effects":results},indent=2))
    print("VFX_BUILD_SUCCESS",len(results),flush=True)
main()
