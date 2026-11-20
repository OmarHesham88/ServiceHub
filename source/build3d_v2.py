"""v2: textured materials (Poly Haven CC0), real furniture models, fixed sky/ground.
Run: <venv>/bin/python build3d_v2.py <outdir> [plan|apt|interior|exterior|web|all] [samples]
Plan coords: x east, z south (m). Blender: X=x, Y=-z, Z=up.
"""
import sys, math, os, random
import bpy, bmesh
from mathutils import Vector, Matrix

OUT = sys.argv[1] if len(sys.argv) > 1 else '.'
WHAT = sys.argv[2] if len(sys.argv) > 2 else 'all'
SAMPLES = int(sys.argv[3]) if len(sys.argv) > 3 else 96
ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')
os.makedirs(OUT, exist_ok=True)

NF, FH, SLAB, H, T = 8, 3.2, .3, 2.8, .15
WALL_H = 2.8   # set lower for cutaway renders
WF = int(os.environ.get('WALK_FLOORS', '1'))   # floors in the walkable model
APTS = [dict(W=11, D=10.5, n=2, opt=dict(back=1, left=1, right=0)),
        dict(W=11, D=10.5, n=2, opt=dict(back=1, left=1, right=0)),
        dict(W=20, D=8.5, n=3, opt=dict(back=1, left=1, right=1))]
BACK = {2: [('bed', 'm', .42), ('bath', '', .16), ('bed', '', .42)],
        3: [('bed', 'm', .34), ('bath', '', .13), ('bed', '', .265), ('bed', '', .265)]}
PLACE = [lambda x, z: (x, 21 - z), lambda x, z: (26 - x, 21 - z), lambda x, z: (3 + x, z)]
EXPOSURE = 0.0

def srgb(h):
    c = [(h >> 16) & 255, (h >> 8) & 255, h & 255]
    f = lambda v: (v / 255) / 12.92 if v / 255 <= .04045 else (((v / 255) + .055) / 1.055) ** 2.4
    return tuple(f(v) for v in c)

# ---------------------------------------------------------------- materials
M, TILE = {}, {}
def _principled(m):
    try: m.use_nodes = True
    except Exception: pass
    return m.node_tree.nodes.get('Principled BSDF'), m.node_tree

def mat(name, color, rough=.6, metal=0., glass=False):
    m = bpy.data.materials.new(name); p, nt = _principled(m)
    p.inputs['Base Color'].default_value = (*color, 1); p.inputs['Roughness'].default_value = rough
    p.inputs['Metallic'].default_value = metal
    if glass:
        p.inputs['Transmission Weight'].default_value = 1.; p.inputs['IOR'].default_value = 1.45
    m.diffuse_color = (*color, 1)
    return m

def tmat(name, tex, tile, tint=None, rough=None, normal=.6, solid=None):
    """Image-textured material. tile = metres covered by one texture repeat (UVs are in metres / tile)."""
    d = os.path.join(ASSETS, 'tex', tex)
    m = bpy.data.materials.new(name); p, nt = _principled(m); N = nt.nodes; L = nt.links
    img = N.new('ShaderNodeTexImage'); img.image = bpy.data.images.load(os.path.join(d, 'diff.jpg'), check_existing=True)
    if solid:
        p.inputs['Base Color'].default_value = (*solid, 1)
    elif tint:
        mix = N.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'
        mix.inputs['Factor'].default_value = 1.0; mix.inputs[7].default_value = (*tint, 1)
        L.new(img.outputs['Color'], mix.inputs[6]); L.new(mix.outputs[2], p.inputs['Base Color'])
    else:
        L.new(img.outputs['Color'], p.inputs['Base Color'])
    rp = os.path.join(d, 'rough.jpg')
    if rough is None and os.path.exists(rp):
        r = N.new('ShaderNodeTexImage'); r.image = bpy.data.images.load(rp, check_existing=True); r.image.colorspace_settings.name = 'Non-Color'
        L.new(r.outputs['Color'], p.inputs['Roughness'])
    else:
        p.inputs['Roughness'].default_value = rough if rough is not None else .6
    np_ = os.path.join(d, 'nor.jpg')
    if normal and os.path.exists(np_):
        n = N.new('ShaderNodeTexImage'); n.image = bpy.data.images.load(np_, check_existing=True); n.image.colorspace_settings.name = 'Non-Color'
        nm = N.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = normal
        L.new(n.outputs['Color'], nm.inputs['Color']); L.new(nm.outputs['Normal'], p.inputs['Normal'])
    TILE[name] = tile
    return m

def make_mats():
    M.clear(); TILE.clear()
    M.update(
        wall=tmat('Plaster', 'white_plaster_02', 2.5, normal=.25, solid=srgb(0xf3efe8), rough=.85),
        facade=tmat('Facade cladding', 'concrete_tile_facade', 3.0, normal=.9, solid=srgb(0xf1ece3), rough=.7),
        neighbour=tmat('Neighbour facade', 'concrete_tile_facade', 4.0, normal=.6, solid=srgb(0xd9d4cb), rough=.8),
        facade2=tmat('Facade stone', 'rectangular_facade_tiles_02', 2.0, tint=srgb(0xd9c6aa), normal=.8),
        parquet=tmat('Herringbone parquet', 'herringbone_parquet', 2.0, normal=.5, rough=.5),
        laminate=tmat('Laminate', 'laminate_floor_02', 2.0, normal=.4, rough=.55),
        kitchen=tmat('Kitchen tiles', 'large_grey_tiles', 1.6, tint=srgb(0xf1efea), normal=.5),
        marble=tmat('Marble tiles', 'marble_tiles', 1.4, normal=.4),
        bathwall=tmat('Bath wall tiles', 'long_white_tiles', 1.0, normal=.5),
        stone=tmat('Marble counter', 'marble_01', 1.5, rough=.15, normal=.2),
        paving=tmat('Paving', 'patterned_paving_02', 3.0, normal=.7),
        grass=tmat('Grass', 'leafy_grass', 3.0, normal=.7),
        road=tmat('Asphalt', 'asphalt_floor', 6.0, normal=.6),
        throw=tmat('Throw fabric', 'fabric_pattern_07', .6, normal=.6, solid=srgb(0x5b7f86), rough=.95),
        rug=tmat('Rug', 'fabric_pattern_07', .4, normal=.8, solid=srgb(0xcfc4b3), rough=1.),
        slab=mat('Slab edge', srgb(0xf4f1ea), .7),
        glass=mat('Glass', srgb(0xbfd6e2), .02, glass=True),
        rail=mat('Rail glass', srgb(0xd6e6ec), .03, glass=True),
        frame=mat('Frame', srgb(0x2e3236), .35, .7),
        sheet=mat('Bed linen', srgb(0xf4f1ea), .9),
        bedbase=mat('Bed upholstery', srgb(0x9a8f82), .95),
        cab=mat('Cabinet matte', srgb(0xeeebe5), .45),
        wood=mat('Walnut', srgb(0x6e4b33), .45),
        dark=mat('Dark', srgb(0x26292c), .3),
        steel=mat('Steel', srgb(0xcfd3d6), .25, .8),
        porcelain=mat('Porcelain', srgb(0xffffff), .12),
        mirror=mat('Mirror', srgb(0xffffff), .02, 1.),
        trunk=mat('Trunk', srgb(0x6b5440), .9),
        leaf=mat('Leaves', srgb(0x4a7536), .8),
        leaf2=mat('Leaves 2', srgb(0x5f8c45), .8),
        bg=mat('Base', srgb(0xe9e6df), .9),
    )

# ---------------------------------------------------------------- mesh builder with box-mapped UVs
class MB:
    def __init__(self, name): self.name = name; self.parts = {}
    def _acc(self, m): return self.parts.setdefault(m, ([], [], []))  # verts, faces, uvs
    def box(self, x1, z1, x2, z2, y0, y1, m):
        if abs(x2 - x1) < 1e-4 or abs(z2 - z1) < 1e-4 or y1 - y0 < 1e-4: return
        X1, X2 = sorted((x1, x2)); Z1, Z2 = sorted((z1, z2))
        v, f, uv = self._acc(m); b = len(v); t = TILE.get(m.name, 1.0)
        P = [(X1, -Z1, y0), (X2, -Z1, y0), (X2, -Z2, y0), (X1, -Z2, y0), (X1, -Z1, y1), (X2, -Z1, y1), (X2, -Z2, y1), (X1, -Z2, y1)]
        v.extend(P)
        for q, ax in [((0, 3, 2, 1), 2), ((4, 5, 6, 7), 2), ((0, 1, 5, 4), 1), ((1, 2, 6, 5), 0), ((2, 3, 7, 6), 1), ((3, 0, 4, 7), 0)]:
            f.append(tuple(b + i for i in q))
            for i in q:
                x, y, z = P[i]
                uv.append((x / t, y / t) if ax == 2 else (x / t, z / t) if ax == 1 else (y / t, z / t))
    def blob(self, cx, cz, cy, r, m, sub=2):
        bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=r)
        v, f, uv = self._acc(m); b = len(v)
        for vert in bm.verts: v.append((cx + vert.co.x, -cz + vert.co.y, cy + vert.co.z * .85))
        for face in bm.faces:
            f.append(tuple(b + vv.index for vv in face.verts)); uv.extend([(0, 0)] * len(face.verts))
        bm.free()
    def emit(self, coll, bevel=0.):
        objs = []
        for m, (v, f, uv) in self.parts.items():
            me = bpy.data.meshes.new(f'{self.name}-{m.name}'); me.from_pydata(v, [], f)
            lay = me.uv_layers.new(name='UVMap')
            for i, l in enumerate(me.loops): lay.data[i].uv = uv[i]
            me.materials.append(m)
            bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
            me.update()
            ob = bpy.data.objects.new(f'{self.name} {m.name}', me); coll.objects.link(ob); objs.append(ob)
            if bevel:
                md = ob.modifiers.new('Bevel', 'BEVEL'); md.width = bevel; md.segments = 3; md.limit_method = 'ANGLE'
                ob.modifiers.new('Smooth', 'WEIGHTED_NORMAL').keep_sharp = True
        return objs

# ---------------------------------------------------------------- furniture library
LIB = {}
def lib(name, decimate=None):
    """Import a Poly Haven model once into a hidden collection; return its root objects."""
    if name in LIB: return LIB[name]
    if os.environ.get('LIGHT'): decimate = {'potted_plant_01': .06, 'bar_chair_round_01': .25, 'street_lamp_01': .2, 'dining_chair_02': .4, 'modern_wooden_cabinet': .4}.get(name, decimate)
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(ASSETS, 'models', name, name + '.gltf'))
    new = [o for o in bpy.data.objects if o not in before]
    hide = bpy.data.collections.get('_lib') or bpy.data.collections.new('_lib')
    if hide.name not in bpy.context.scene.collection.children: bpy.context.scene.collection.children.link(hide)
    hide.hide_render = True; hide.hide_viewport = True
    for o in new:
        if o.type == 'MESH' and decimate:          # simplify while the object is still visible (hidden objects are not evaluated)
            bm = bmesh.new(); bm.from_mesh(o.data); n0 = len(bm.faces); bm.free()
            md = o.modifiers.new('Dec', 'DECIMATE'); md.ratio = decimate
            bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get()
            me = bpy.data.meshes.new_from_object(o.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
            o.modifiers.clear(); o.data = me
            print('decimated', o.name, n0, '->', len(me.polygons), flush=True)
        for c in list(o.users_collection): c.objects.unlink(o)
        hide.objects.link(o)
    # flatten hierarchy to mesh objects with baked world transforms
    meshes = []
    for o in new:
        if o.type == 'MESH':
            o.data = o.data.copy(); o.data.transform(o.matrix_world); o.parent = None; o.matrix_world = Matrix.Identity(4)
            meshes.append(o)
    LIB[name] = meshes
    return meshes

def place(coll, name, Tr, lx, lz, face=(0, 1), y=0., scale=1., decimate=None):
    """Place model at local apt coords (lx,lz) facing local direction `face` (plan dx,dz). Default model front = plan +z."""
    wx, wz = Tr(lx, lz); fx, fz = Tr(lx + face[0], lz + face[1]); dx, dz = fx - wx, fz - wz
    ang = math.atan2(-dz, dx) - math.atan2(-1, 0)
    for src in lib(name, decimate):
        o = bpy.data.objects.new(src.name, src.data)   # linked duplicate: shares mesh -> written once in glTF
        o.location = (wx, -wz, y); o.rotation_euler = (0, 0, ang); o.scale = (scale,) * 3
        coll.objects.link(o)

# ---------------------------------------------------------------- typical floor
def apt_rooms(A):
    W, D = A['W'], A['D']; zb, xk, zk, xe = D * .42, W * .62, D * .72, W * .8
    R = []; x = 0
    for t, n, fr in BACK[A['n']]: R.append(dict(t=t, m=n == 'm', x1=x, z1=0, x2=x + fr * W, z2=zb)); x += fr * W
    R += [dict(t='liv', x1=0, z1=zb, x2=xk, z2=D), dict(t='kit', x1=xk, z1=zb, x2=W, z2=zk),
          dict(t='bath', x1=xk, z1=zk, x2=xe, z2=D), dict(t='ent', x1=xe, z1=zk, x2=W, z2=D)]
    return R, (zb, xk, zk, xe)

def build_floor(mb, y, furn=None, exterior=False, only=None, stairs='old', top=False):
    """furn: collection for furniture models (None = no furniture). only: apartment index to build alone."""
    soft = MB(mb.name + ' soft')   # bevelled custom furniture
    wallm = M['facade'] if exterior else M['wall']
    for i, A in enumerate(APTS):
        if only is not None and i != only: continue
        Tr = PLACE[i]; W, D = A['W'], A['D']
        R, (zb, xk, zk, xe) = apt_rooms(A)
        def B(x1, z1, x2, z2, y0, y1, m, tgt=mb):
            a = Tr(x1, z1); b = Tr(x2, z2); tgt.box(a[0], a[1], b[0], b[1], y + y0, y + y1, m)
        def wall(x1, z1, x2, z2, kind=None, g=0, outer=False, wm=None):
            hz = z1 == z2; wm = wm or (wallm if outer else M['wall'])
            def seg(a, b, y0, y1, m):
                y1 = min(y1, WALL_H)
                if b - a <= .01 or y1 <= y0: return
                if hz: B(a, z1 - T / 2, b, z1 + T / 2, y0, y1, m)
                else: B(x1 - T / 2, a, x1 + T / 2, b, y0, y1, m)
            s, e = (x1, x2) if hz else (z1, z2)
            if kind == 'door':
                mid = (s + e) / 2; h = g / 2
                seg(s, mid - h, 0, H, wm); seg(mid + h, e, 0, H, wm); seg(mid - h, mid + h, 2.1, H, wm)
                # door frame
                if hz: B(mid - h - .04, z1 - .1, mid - h, z1 + .1, 0, 2.1, M['wood']); B(mid + h, z1 - .1, mid + h + .04, z1 + .1, 0, 2.1, M['wood'])
                else: B(x1 - .1, mid - h - .04, x1 + .1, mid - h, 0, 2.1, M['wood']); B(x1 - .1, mid + h, x1 + .1, mid + h + .04, 0, 2.1, M['wood'])
            elif kind == 'win':
                p = min(.45, (e - s) / 4)
                seg(s, s + p, 0, H, wm); seg(e - p, e, 0, H, wm); seg(s + p, e - p, 0, .45, wm); seg(s + p, e - p, 2.45, H, wm)
                seg(s + p, e - p, .45, 2.45, M['glass'])
                n = max(1, round((e - s - 2 * p) / 1.4))
                for k in range(n + 1):
                    q = s + p + k * (e - s - 2 * p) / n
                    if hz: B(q - .025, z1 - .05, q + .025, z1 + .05, .45, min(2.45, WALL_H), M['frame'])
                    else: B(x1 - .05, q - .025, x1 + .05, q + .025, .45, min(2.45, WALL_H), M['frame'])
                for yy in ([.43] + ([2.43] if WALL_H > 2.47 else [])):
                    if hz: B(s + p, z1 - .06, e - p, z1 + .06, yy, yy + .04, M['frame'])
                    else: B(x1 - .06, s + p, x1 + .06, e - p, yy, yy + .04, M['frame'])
            else:
                seg(s, e, 0, H, wm)
        for r in R:
            if r['z1'] == 0:
                wall(r['x1'], 0, r['x2'], 0, 'win' if r['t'] != 'bath' and A['opt']['back'] else None, outer=True)
                wall(r['x1'], zb, r['x2'], zb, 'door', .9)
                if r['x1'] > 0: wall(r['x1'], 0, r['x1'], zb)
        wall(0, D, xk, D, outer=i == 2); wall(xk, D, xe, D, outer=i == 2); wall(xe, D, W, D, 'door', 1.1)
        wall(0, 0, 0, zb, 'win' if A['opt']['left'] else None, outer=True)
        wall(0, zb, 0, D, 'win' if A['opt']['left'] else None, outer=True)
        wall(W, 0, W, zb, 'win' if A['opt']['right'] else None, outer=A['opt']['right'] == 1)
        wall(W, zb, W, D, outer=i == 2)
        wall(xk, zk, xk, D, 'door', .8); wall(xk, zk, xe, zk); wall(xe, zk, xe, D)
        FL = dict(bed=M['laminate'], liv=M['parquet'], kit=M['kitchen'], bath=M['marble'], ent=M['marble'])
        for r in R:
            B(r['x1'], r['z1'], r['x2'], r['z2'], 0, .02, FL[r['t']])
            # skirting
            if r['t'] in ('bed', 'liv'):
                for a in [(r['x1'], r['z1'], r['x2'], r['z1'] + .09), (r['x1'], r['z2'] - .09, r['x2'], r['z2']),
                          (r['x1'], r['z1'], r['x1'] + .09, r['z2']), (r['x2'] - .09, r['z1'], r['x2'], r['z2'])]:
                    B(*a, .02, .1, M['cab'])
        if furn is None: continue
        for r in R:
            x1, z1, x2, z2 = r['x1'], r['z1'], r['x2'], r['z2']; w, d = x2 - x1, z2 - z1; cx, cz = (x1 + x2) / 2, (z1 + z2) / 2
            if r['t'] == 'bed':
                bw = 1.8 if r['m'] else 1.2
                B(cx - (bw + .5) / 2, .08, cx + (bw + .5) / 2, .2, .0, 1.2, M['bedbase'], soft)            # headboard
                B(cx - (bw + .1) / 2, .2, cx + (bw + .1) / 2, 2.32, .05, .38, M['bedbase'], soft)            # base
                B(cx - bw / 2, .24, cx + bw / 2, 2.28, .38, .6, M['sheet'], soft)                             # mattress
                B(cx - (bw + .08) / 2, 1.55, cx + (bw + .08) / 2, 2.3, .6, .65, M['throw'], soft)             # throw
                place(furn, 'throw_pillows_01', Tr, cx, .55, (0, 1), y + .6, .85 if r['m'] else .6)
                if w > bw + 1.4:
                    for s in (-1, 1):
                        nx = cx + s * (bw / 2 + .45); place(furn, 'side_table_01', Tr, nx, .4, (0, 1), y)
                        if s == 1: place(furn, 'potted_plant_04', Tr, nx, .4, (0, 1), y + .55)
                ww = min(2.2, w / 2 - .7)
                if ww > .6:
                    B(x1 + .2, z2 - .72, x1 + .2 + ww, z2 - .12, 0, 2.4, M['wood'], soft)
                    for k in range(1, int(ww / .55) + 1):
                        q = x1 + .2 + k * ww / (int(ww / .55) + 1); B(q - .006, z2 - .735, q + .006, z2 - .72, .05, 2.35, M['dark'])
            elif r['t'] == 'bath':
                B(x1 + .02, z1 + .02, x2 - .02, z1 + .1, 0, 2.1, M['bathwall'])
                B(x2 - 1.05, .1, x2 - .1, 1.03, 0, .05, M['porcelain'], soft)
                B(x2 - 1.07, .1, x2 - 1.05, 1.03, .05, 2.0, M['glass'])
                B(x1 + .12, z2 - .85, x1 + .52, z2 - .3, 0, .42, M['porcelain'], soft)
                B(x1 + .1, cz - .3, x1 + .55, cz + .55, .25, .8, M['wood'], soft)
                B(x1 + .08, cz - .32, x1 + .57, cz + .57, .8, .84, M['stone'])
                B(x1 + .02, cz - .3, x1 + .05, cz + .55, 1.1, 1.9, M['mirror'])
            elif r['t'] == 'liv':
                big = w > 9
                xc = x1 + (w * .45 if big else 3.85)
                place(furn, 'modern_wooden_cabinet', Tr, xc, z1 + .33, (0, 1), y, .85)
                B(xc - .85, z1 + .08, xc + .85, z1 + .12, 1.0, 1.95, M['dark'])                                # TV on solid wall
                place(furn, 'sofa_03', Tr, xc, z1 + 3.55, (0, -1), y)
                place(furn, 'modern_coffee_table_01', Tr, xc, z1 + 2.1, (1, 0), y)
                place(furn, 'modern_arm_chair_01', Tr, xc + 2.3, z1 + 2.1, (-1, 0), y)
                B(xc - 1.7, z1 + 1.0, xc + 1.7, z1 + 3.1, .02, .03, M['rug'])
                place(furn, 'potted_plant_01', Tr, x1 + .5, z1 + .5, (1, 0), y, 1., decimate=.12)
                # dining for 4 by the window (custom walnut table)
                if big: tx, tz, along_z = x2 - 2.0, z1 + 2.4, False
                else: tx, tz, along_z = x1 + 1.0, z2 - 1.35, True
                hw, hd = (.45, .8) if along_z else (.8, .45)
                B(tx - hw, tz - hd, tx + hw, tz + hd, .72, .76, M['wood'], soft)
                for sx in (-1, 1):
                    for sz in (-1, 1):
                        B(tx + sx * (hw - .08) - .03, tz + sz * (hd - .08) - .03, tx + sx * (hw - .08) + .03, tz + sz * (hd - .08) + .03, 0, .72, M['dark'])
                if along_z:
                    place(furn, 'dining_chair_02', Tr, tx, tz - hd - .3, (0, 1), y); place(furn, 'dining_chair_02', Tr, tx, tz + hd + .28, (0, -1), y)
                    place(furn, 'dining_chair_02', Tr, tx + hw + .32, tz + .35, (-1, 0), y)
                else:
                    for sx in (-.4, .4):
                        place(furn, 'dining_chair_02', Tr, tx + sx, tz - hd - .3, (0, 1), y); place(furn, 'dining_chair_02', Tr, tx + sx, tz + hd + .3, (0, -1), y)
            elif r['t'] == 'kit':
                L = d - 1.2; kz = z1 + .9
                B(W - .7, kz, W - .08, kz + L, .1, .88, M['wood'], soft); B(W - .72, kz, W - .08, kz + L, .88, .92, M['stone'])
                B(W - .1, kz, W - .08, kz + L, .92, 1.5, M['bathwall']); B(W - .42, kz, W - .08, kz + L, 1.55, 2.3, M['cab'], soft)
                B(W - .45, kz + L * .2, W - .1, kz + L * .45, .925, .935, M['dark'])                         # hob
                B(W - .85, z1 + .1, W - .1, z1 + .82, 0, 2.0, M['steel'], soft)                               # fridge
                if w > 3.6:
                    ix = x1 + w * .42
                    B(ix - .85, cz - .42, ix + .85, cz + .42, .1, .88, M['wood'], soft); B(ix - .9, cz - .47, ix + .9, cz + .47, .88, .93, M['stone'])
                    for s in (-.45, .45): place(furn, 'bar_chair_round_01', Tr, ix + s, cz - .85, (0, 1), y)
            elif r['t'] == 'ent':
                B(W - .45, D - 2.2, W - .1, D - .95, .15, .9, M['wood'], soft)
                B(W - .04, D - 2.1, W - .02, D - 1.05, 1.1, 2.0, M['mirror'])
    if only is None:
        mb.box(3, 8.5, 23, 10.5, y, y + .02, M['marble'])
        if stairs != 'walk': mb.box(11, 10.5, 15, 21, y, y + .02, M['marble'])
        mb.box(11, 21 - T / 2, 15, 21 + T / 2, y, y + .9, wallm); mb.box(11, 21 - T / 2, 15, 21 + T / 2, y + .9, y + 2.45, M['glass'])
        mb.box(11, 21 - T / 2, 15, 21 + T / 2, y + 2.45, y + H, wallm)
        mb.box(3 - T / 2, 8.5, 3 + T / 2, 10.5, y, y + H, wallm); mb.box(23 - T / 2, 8.5, 23 + T / 2, 10.5, y, y + H, wallm)
        if stairs == 'walk':
            stairs_walk(mb, y, top)
        elif furn is not None:
            for k in range(10):
                mb.box(11.1, 12 + k * .5, 12.9, 12.5 + k * .5, y, y + (k + 1) * .16, M['marble'])
                mb.box(13.1, 17 - (k + 1) * .5, 14.9, 17 - k * .5, y, y + (k + 1) * .144, M['marble'])
            mb.box(11.1, 17, 14.9, 18.5, y, y + 1.6, M['marble'])
            mb.box(12.95, 12, 13.05, 17, y, y + 1.0, M['frame'])
    return soft

def stairs_walk(mb, y, top=False, ground=False):
    """Dog-leg stair in the core (x 11-15, z 12-18.5): flight A up +z on x 11.1-12.9, landing z 17-18.5, flight B back on x 13.1-14.9."""
    mb.box(11, 10.5, 15, 12, y, y + .02, M['marble']); mb.box(11, 18.5, 15, 21, y, y + .02, M['marble'])
    if not ground: mb.box(11, 18.45, 15, 18.55, y, y + 1.0, M['frame'])                 # rail: pocket in front of the stair void
    if top:
        mb.box(11, 11.95, 13, 12.05, y, y + 1.0, M['frame'])                             # rail around the last stair void
        mb.box(12.95, 12, 13.05, 18.5, y, y + 1.0, M['frame'])
        return
    mb.box(12.95, 12, 13.05, 17, y, y + FH - SLAB, M['wall'])                            # wall between the flights
    for k in range(10):
        t = y + (k + 1) * .16; mb.box(11.1, 12 + k * .5, 12.9, 12.5 + k * .5, t - .22, t, M['marble'])
        t2 = y + 1.6 + (k + 1) * .16; mb.box(13.1, 17 - (k + 1) * .5, 14.9, 17 - k * .5, t2 - .22, t2, M['marble'])
    mb.box(11.1, 17, 14.9, 18.5, y + 1.38, y + 1.6, M['marble'])                        # half landing
    if ground:                                                                           # close the space under the first flights
        mb.box(11 - T / 2, 12, 11 + T / 2, 18.5, y, y + FH - SLAB, M['wall']); mb.box(15 - T / 2, 12, 15 + T / 2, 18.5, y, y + FH - SLAB, M['wall'])
        mb.box(11, 18.5 - T / 2, 15, 18.5 + T / 2, y, y + 1.38, M['wall']); mb.box(13, 12 - T / 2, 15, 12 + T / 2, y, y + FH - SLAB, M['wall'])

def parent_to(coll, name):
    e = bpy.data.objects.new(name, None); coll.objects.link(e)
    for o in list(coll.objects):
        if o is not e and o.parent is None: o.parent = e
    return e

def build_walk(root):
    """Walkable building: street -> lobby -> stairs -> 8 furnished floors."""
    global H
    H = FH - SLAB
    for f in range(1, WF + 1):
        y = f * FH; mb = MB(f'Floor {f}'); fc = coll(f'Furn {f}')
        soft = build_floor(mb, y, fc, exterior=False, stairs='walk', top=(f == WF))
        for x1, x2 in [(.4, 10.6), (15.4, 25.6)]:
            mb.box(x1, 21, x2, 22.6, y - .02, y + .18, M['slab']); mb.box(x1, 22.52, x2, 22.6, y + .18, y + 1.15, M['rail'])
            mb.box(x1, 22.5, x2, 22.62, y + 1.12, y + 1.18, M['frame'])
        mb.emit(root); soft.emit(fc); parent_to(fc, f'Furn {f}')
    mb = MB('Structure')
    for f in range(1, WF + 1):          # slabs with the stair void
        y = f * FH
        for a in [(0, 10.5, 11, 21), (15, 10.5, 26, 21), (11, 10.5, 15, 12), (11, 18.5, 15, 21), (3, 0, 23, 10.5)]:
            mb.box(a[0] - (.1 if a[0] in (0, 3) else 0), a[1] - (.1 if a[1] == 0 else 0), a[2] + (.1 if a[2] in (26, 23) else 0), a[3] + (.1 if a[3] == 21 else 0), y - SLAB, y, M['slab'])
    ry = (WF + 1) * FH
    for x1, x2, z1, z2 in [(0, 26, 10.5, 21), (3, 23, 0, 10.5)]:
        mb.box(x1 - .1, z1 - .1, x2 + .1, z2 + .1, ry - SLAB, ry, M['slab'])
        for a in [(x1, z1, x2, z1 + .2), (x1, z2 - .2, x2, z2), (x1, z1, x1 + .2, z2), (x2 - .2, z1, x2, z2)]:
            mb.box(*a, ry, ry + 1.0, M['facade'])
    for x in (-.2, 25.8): mb.box(x, 20.85, x + .4, 21.35, 0, ry + 1, M['facade2'])
    # ground floor lobby
    gh = FH - SLAB
    mb.box(0, 10.5, 26, 21, -.02, .02, M['marble']); mb.box(3, 0, 23, 10.5, -.02, .02, M['marble'])
    for x1, x2 in [(0, 12), (14, 26)]: mb.box(x1, 20.95, x2, 21.05, .02, gh, M['glass'])
    for k in range(14):
        x = k * 2
        if not 12 < x < 14: mb.box(x - .04, 20.9, x + .04, 21.1, 0, gh, M['frame'])
    for x in (12, 14): mb.box(x - .06, 20.88, x + .06, 21.12, 0, gh, M['frame'])
    mb.box(12, 20.88, 14, 21.12, 2.3, gh, M['frame'])                                     # door head
    for a in [(0, 10.5, .2, 21), (25.8, 10.5, 26, 21), (3, 0, 23, .2), (3, 0, 3.2, 10.5), (22.8, 0, 23, 10.5), (0, 10.5, 3, 10.7), (23, 10.5, 26, 10.7)]:
        mb.box(*a, 0, gh, M['facade2'])
    stairs_walk(mb, 0, ground=True)
    mb.box(8.5, 21, 17.5, 24.6, FH - .55, FH - .2, M['dark'])
    for sx in (-1, 1): mb.box(13 + sx * 4 - .1, 24.2, 13 + sx * 4 + .1, 24.4, 0, FH - .55, M['dark'])
    mb.box(9, 24.55, 17, 24.66, FH - .5, FH - .25, M['facade2'])
    mb.box(3.5, 14, 7.5, 15, 0, 1.05, M['wood']); mb.box(3.4, 13.9, 7.6, 15.1, 1.05, 1.1, M['stone'])   # reception desk
    mb.box(.25, 12, .3, 19, 0, 2.6, M['wood'])                                                          # wood wall panel
    mb.emit(root)
    lc = coll('Furn 0')
    place(lc, 'sofa_03', lambda a, b: (a, b), 20, 15.5, (-1, 0), 0)
    place(lc, 'sofa_03', lambda a, b: (a, b), 23.5, 15.5, (-1, 0), 0) if False else None
    place(lc, 'modern_coffee_table_01', lambda a, b: (a, b), 18.6, 15.5, (0, 1), 0)
    place(lc, 'modern_arm_chair_01', lambda a, b: (a, b), 17.2, 15.5, (1, 0), 0)
    for (x, z) in [(1, 20), (25, 20), (10.3, 20.2), (15.7, 20.2), (4, 2), (22, 2)]:
        place(lc, 'potted_plant_01', lambda a, b: (a, b), x, z, (0, 1), 0, 1., decimate=.12)
    parent_to(lc, 'Furn 0')
    build_site(coll('Site'), big=False)

# ---------------------------------------------------------------- building & site
def build_building(coll):
    for f in range(1, NF + 1):
        mb = MB(f'Floor {f}'); y = f * FH
        build_floor(mb, y, None, exterior=True)
        for x1, x2 in [(.4, 10.6), (15.4, 25.6)]:
            mb.box(x1, 21, x2, 22.6, y - .02, y + .18, M['slab'])
            mb.box(x1, 22.52, x2, 22.6, y + .18, y + 1.15, M['rail'])
            mb.box(x1, 22.5, x2, 22.62, y + 1.12, y + 1.18, M['frame'])
        mb.emit(coll)
    mb = MB('Structure')
    for f in range(1, NF + 2):
        y = f * FH
        for x1, x2, z1, z2 in [(0, 26, 10.5, 21), (3, 23, 0, 10.5)]:
            mb.box(x1 - .1, z1 - .1, x2 + .1, z2 + .1, y - SLAB, y, M['slab'])
    ry = (NF + 1) * FH
    for x1, x2, z1, z2 in [(0, 26, 10.5, 21), (3, 23, 0, 10.5)]:
        for a in [(x1, z1, x2, z1 + .2), (x1, z2 - .2, x2, z2), (x1, z1, x1 + .2, z2), (x2 - .2, z1, x2, z2)]:
            mb.box(*a, ry, ry + 1.0, M['facade'])
    mb.box(11, 12, 15, 19, ry, ry + 3, M['facade'])
    for x in (-.2, 25.8): mb.box(x, 20.85, x + .4, 21.35, 0, ry + 1, M['facade2'])
    mb.box(11, 20.85, 15, 21.4, FH, ry + 1, M['facade2'])
    for f in range(1, NF + 1): mb.box(11.6, 21.38, 14.4, 21.45, f * FH + .7, f * FH + 2.6, M['glass'])
    mb.box(0, 10.5, 26, 21, -.02, .05, M['marble']); mb.box(3, 0, 23, 10.5, -.02, .05, M['marble'])
    mb.box(0, 20.95, 26, 21.05, .05, FH - .3, M['glass'])
    for k in range(14): mb.box(k * 2 - .04, 20.9, k * 2 + .04, 21.1, .05, FH - .3, M['frame'])
    for a in [(0, 10.5, .2, 21), (25.8, 10.5, 26, 21), (3, 0, 23, .2), (3, 0, 3.2, 10.5), (22.8, 0, 23, 10.5), (0, 10.5, 3, 10.7), (23, 10.5, 26, 10.7)]:
        mb.box(*a, 0, FH - SLAB, M['facade2'])
    mb.box(8.5, 21, 17.5, 24.6, FH - .55, FH - .2, M['dark'])
    for s in (-1, 1): mb.box(13 + s * 4 - .1, 24.2, 13 + s * 4 + .1, 24.4, 0, FH - .55, M['dark'])
    mb.box(9, 24.55, 17, 24.66, FH - .5, FH - .25, M['facade2'])
    mb.emit(coll)

def build_site(coll, big=True):
    mb = MB('Site'); random.seed(7)
    R = 400 if big else 60
    mb.box(-R, -R, R, R, -.14, -.04, M['grass'])
    mb.box(-R, 31, R, 41, -.1, -.01, M['road'])
    for z in (35.9, 36.1): mb.box(-R, z - .06, R, z + .06, -.01, -.005, M['porcelain'])
    mb.box(-60, 21, 90, 31, -.1, .03, M['paving'])
    mb.box(-6, -6, 32, 21, -.1, .0, M['paving'])
    for (x1, x2) in [(-4, 6.5), (19.5, 30)]: mb.box(x1, 25, x2, 29, -.1, .07, M['grass'])
    for (x, z) in [(-2, 27), (3, 27.5), (22, 27.5), (28, 27), (-9, 15), (-9, 5), (35, 15), (35, 5), (42, 26), (-16, 26), (-24, 26), (50, 26)]:
        h = 3 + random.random() * 1.5
        mb.box(x - .12, z - .12, x + .12, z + .12, 0, h, M['trunk'])
        for k in range(6):
            mb.blob(x + random.uniform(-.9, .9), z + random.uniform(-.9, .9), h + random.uniform(.1, 1.6), random.uniform(.8, 1.3),
                    M['leaf'] if k % 2 else M['leaf2'], sub=2)
    # neighbouring blocks (simple, light) for context
    for (x1, z1, x2, z2, hh) in [(-48, -5, -26, 18, 18), (48, -8, 70, 16, 24), (8, 50, 40, 70, 21), (52, 50, 80, 72, 12)]:
        mb.box(x1, z1, x2, z2, 0, hh, M['neighbour'])
    mb.emit(coll)
    for x in (-10, 6, 20, 36):
        place(coll, 'street_lamp_01', lambda a, b: (a, b), x, 30.6, (0, 1), 0)

# ---------------------------------------------------------------- scene helpers
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True); LIB.clear(); make_mats()

def world(kind='sky', el=38, az=200):
    w = bpy.data.worlds.new('World'); bpy.context.scene.world = w
    try: w.use_nodes = True
    except Exception: pass
    nt = w.node_tree; bg = nt.nodes.get('Background')
    if kind == 'studio':
        bg.inputs['Color'].default_value = (.86, .87, .88, 1); bg.inputs['Strength'].default_value = .8; return
    sky = nt.nodes.new('ShaderNodeTexSky')
    for t in ('MULTIPLE_SCATTERING', 'NISHITA', 'SINGLE_SCATTERING', 'HOSEK_WILKIE'):
        try: sky.sky_type = t; break
        except Exception: pass
    for k, v in dict(sun_elevation=math.radians(el), sun_rotation=math.radians(az), altitude=200., air_density=1.2, dust_density=1.5).items():
        try: setattr(sky, k, v)
        except Exception: pass
    try: sky.sun_disc = False
    except Exception: pass
    nt.links.new(sky.outputs['Color'], bg.inputs['Color']); bg.inputs['Strength'].default_value = .3

def sun(energy=3.5, el=38, az=200):
    s = bpy.data.lights.new('Sun', 'SUN'); s.energy = energy; s.angle = math.radians(2)
    o = bpy.data.objects.new('Sun', s); bpy.context.scene.collection.objects.link(o)
    o.rotation_euler = (math.radians(90 - el), 0, math.radians(az))

def area(loc, size, energy, color=(1, .93, .84)):
    l = bpy.data.lights.new('Area', 'AREA'); l.size = size; l.energy = energy; l.color = color
    o = bpy.data.objects.new('Area', l); bpy.context.scene.collection.objects.link(o); o.location = loc

def camera(loc, target, lens=35):
    for ob in list(bpy.data.objects):
        if ob.type == 'CAMERA': bpy.data.objects.remove(ob)
    c = bpy.data.cameras.new('Cam'); c.lens = lens; c.clip_start = .05; c.clip_end = 3000
    o = bpy.data.objects.new('Cam', c); bpy.context.scene.collection.objects.link(o)
    o.location = loc; o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    bpy.context.scene.camera = o

def render(path, w, h, samples=SAMPLES):
    sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'
    sc.cycles.samples = samples; sc.cycles.use_denoising = True; sc.cycles.max_bounces = 6
    try: sc.cycles.denoiser = 'OPENIMAGEDENOISE'
    except Exception: pass
    sc.render.resolution_x, sc.render.resolution_y = w, h; sc.render.resolution_percentage = 100
    try: sc.view_settings.view_transform = 'AgX'
    except Exception: sc.view_settings.view_transform = 'Filmic'
    try: sc.view_settings.look = 'AgX - Medium High Contrast'
    except Exception: sc.view_settings.look = 'None'
    sc.view_settings.exposure = EXPOSURE
    sc.render.filepath = path; sc.render.image_settings.file_format = 'PNG'
    bpy.ops.render.render(write_still=True); print('wrote', path, flush=True)

def coll(name):
    c = bpy.data.collections.new(name); bpy.context.scene.collection.children.link(c); return c

def floor_scene(only=None):
    c = coll('Floor'); mb = MB('Typical floor'); soft = build_floor(mb, 0, c, only=only); mb.emit(c); soft.emit(c, bevel=.025)
    return c

# ---------------------------------------------------------------- jobs
def job_plan():
    global EXPOSURE, WALL_H; EXPOSURE = .1; WALL_H = 2.2
    reset(); world('studio'); sun(2.6, 52, 150)
    floor_scene()
    b = MB('Base'); b.box(-1.5, -1.5, 27.5, 22.5, -.3, 0, M['bg']); b.emit(coll('Base'))
    camera((2, -40, 30), (13, -10.5, 0), 30); render(f'{OUT}/plan3d.png', 1800, 1200)

def job_apt():
    global EXPOSURE, WALL_H; EXPOSURE = .1; WALL_H = 2.2
    reset(); world('studio'); sun(2.6, 55, 140)
    floor_scene(only=0)
    b = MB('Base'); b.box(-1, 9.5, 12, 22, -.3, 0, M['bg']); b.emit(coll('Base'))
    camera((5.6, -31.5, 15.5), (5.6, -15.4, 0), 32); render(f'{OUT}/apt1-3d.png', 1800, 1200)

def job_interior():
    """Eye-level view of apartment 1 living room, with a ceiling and soft lights."""
    global EXPOSURE, WALL_H; EXPOSURE = .2; WALL_H = 2.8
    reset(); world('sky', 35, 200); sun(3.0, 35, 200)
    floor_scene(only=0)
    c = MB('Ceiling'); c.box(-.3, 10.2, 11.3, 21.3, H, H + .2, M['slab']); c.box(-.5, 10, 11.5, 21.5, -.3, 0, M['bg']); c.emit(coll('Ceil'))
    build_site(coll('Site'))
    for (x, z) in [(3.6, 14.4), (1.5, 12.0), (5.5, 11.5)]:
        area((x, -z, H - .05), 1.2, 45)
    # camera: inside living room near kitchen side, looking towards sofa/TV & window wall
    camera((6.45, -11.1, 1.5), (1.6, -16.2, 1.0), 18)
    render(f'{OUT}/interior-living.png', 1800, 1200)

def job_exterior():
    global EXPOSURE, WALL_H; EXPOSURE = 0.; WALL_H = 2.8
    reset(); world('sky', 32, 210); sun(3.6, 32, 210)
    build_building(coll('Building')); build_site(coll('Site'))
    camera((-24, -62, 7), (11, -14, 13), 32); render(f'{OUT}/exterior-street.png', 1800, 1200)
    camera((60, -80, 48), (12, -10, 10), 38); render(f'{OUT}/exterior-aerial.png', 1800, 1200)

def job_web():
    """GLB models for the browser: textures downsized, plants decimated."""
    global WALL_H; WALL_H = 2.8
    def shrink():
        for img in bpy.data.images:
            if img.size[0] > 512:
                img.scale(512, int(512 * img.size[1] / img.size[0]))
    def export(path):
        bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', export_apply=True,
                                  export_image_format='JPEG', export_jpeg_quality=80, use_visible=True)
    reset(); build_building(coll('Building')); build_site(coll('Site'), big=False); shrink(); export(f'{OUT}/building.glb')
    reset(); floor_scene(); shrink(); export(f'{OUT}/typical-floor.glb')

def job_walk():
    global WALL_H; WALL_H = 3.0
    def shrink():
        for img in bpy.data.images:
            if img.size[0] > 512: img.scale(512, int(512 * img.size[1] / img.size[0]))
    reset(); build_walk(coll('Walk')); shrink()
    bpy.ops.export_scene.gltf(filepath=f'{OUT}/walk.glb', export_format='GLB', export_apply=True,
                              export_image_format='JPEG', export_jpeg_quality=80, use_visible=True)
    print('wrote walk.glb', flush=True)

JOBS = dict(walk=job_walk, plan=job_plan, apt=job_apt, interior=job_interior, exterior=job_exterior, web=job_web)
for name in (JOBS if WHAT == 'all' else WHAT.split(',')):
    JOBS[name]()
