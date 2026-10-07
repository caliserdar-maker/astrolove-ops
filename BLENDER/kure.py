# Blender: tek altin malzeme, ortografik kure render (malzeme haritasi). Kullanim: blender -b -P kure.py -- hdri purluluk renk_r renk_g renk_b donus cikti
import bpy, sys, math, time
T = time.time()
a = sys.argv[sys.argv.index('--') + 1:]
hdri, rough, cr, cg, cb, don, out = a[0], float(a[1]), float(a[2]), float(a[3]), float(a[4]), float(a[5]), a[6]
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
bpy.ops.mesh.primitive_uv_sphere_add(segments=1024, ring_count=512, radius=1.0)
ob = bpy.context.active_object
bpy.ops.object.shade_smooth()
mat = bpy.data.materials.new('altin'); mat.use_nodes = True
b = mat.node_tree.nodes['Principled BSDF']
b.inputs['Base Color'].default_value = (cr, cg, cb, 1)
b.inputs['Metallic'].default_value = 1.0
b.inputs['Roughness'].default_value = rough
ob.data.materials.append(mat)
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
nt = w.node_tree
env = nt.nodes.new('ShaderNodeTexEnvironment')
env.image = bpy.data.images.load(hdri if '/' in hdri else f'/home/claude/blender/venv/lib/python3.13/site-packages/bpy/5.2/datafiles/studiolights/world/{hdri}.exr')
mp = nt.nodes.new('ShaderNodeMapping'); tc = nt.nodes.new('ShaderNodeTexCoord')
mp.inputs['Rotation'].default_value = (0, 0, math.radians(don))
nt.links.new(tc.outputs['Generated'], mp.inputs['Vector']); nt.links.new(mp.outputs['Vector'], env.inputs['Vector'])
nt.links.new(env.outputs['Color'], nt.nodes['Background'].inputs['Color'])
cd = bpy.data.cameras.new('cam'); cd.type = 'ORTHO'; cd.ortho_scale = 2.0
cam = bpy.data.objects.new('cam', cd); cam.location = (0, 0, 10); sc.collection.objects.link(cam); sc.camera = cam
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = int(__import__("os").environ.get("ORNEK","256")); sc.cycles.use_denoising = False
sc.render.resolution_x = sc.render.resolution_y = 1024; sc.render.resolution_percentage = 100
sc.render.film_transparent = True
sc.render.image_settings.file_format = 'OPEN_EXR'; sc.render.image_settings.color_depth = '32'
sc.view_settings.view_transform = 'Standard'
sc.render.filepath = out
bpy.ops.render.render(write_still=True)
print('kure bitti', round(time.time() - T, 1), 'sn')
