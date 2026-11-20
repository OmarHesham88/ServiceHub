import json, os, sys, urllib.request
OUT = sys.argv[1]
def get(u): 
    req = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0 (asset-fetch)'})
    with urllib.request.urlopen(req, timeout=60) as r: return r.read()
# CC0 textures and models from polyhaven.com
TEX = ['herringbone_parquet','laminate_floor_02','marble_tiles','large_grey_tiles','long_white_tiles','white_plaster_02',
       'concrete_tile_facade','rectangular_facade_tiles_02','patterned_paving_02','leafy_grass','asphalt_floor','marble_01','fabric_pattern_07']
MOD = ['sofa_03','modern_arm_chair_01','modern_coffee_table_01','dining_table','dining_chair_02','side_table_01',
       'modern_wooden_cabinet','potted_plant_01','potted_plant_04','pachira_aquatica_01','modern_ceiling_lamp_01','throw_pillows_01',
       'shrub_01','tree_small_02','street_lamp_01','bar_chair_round_01']
for t in TEX:
    d = os.path.join(OUT, 'tex', t); os.makedirs(d, exist_ok=True)
    f = json.loads(get(f'https://api.polyhaven.com/files/{t}'))
    for key, name in [('Diffuse','diff'),('nor_gl','nor'),('Rough','rough')]:
        if key == 'Diffuse' and key not in f:   # some fabrics name their colour map col_1
            key = next((k for k in ('col_1', 'col_01', 'col_2') if k in f), key)
        if key in f and '1k' in f[key]:
            u = f[key]['1k']['jpg']['url']; p = os.path.join(d, name + '.jpg')
            if not os.path.exists(p): open(p,'wb').write(get(u))
    print('tex', t, flush=True)
for m in MOD:
    d = os.path.join(OUT, 'models', m); os.makedirs(d, exist_ok=True)
    f = json.loads(get(f'https://api.polyhaven.com/files/{m}'))
    g = f['gltf']['1k']['gltf']
    p = os.path.join(d, m + '.gltf')
    if not os.path.exists(p): open(p,'wb').write(get(g['url']))
    for rel, inc in g.get('include', {}).items():
        q = os.path.join(d, rel); os.makedirs(os.path.dirname(q), exist_ok=True)
        if not os.path.exists(q): open(q,'wb').write(get(inc['url']))
    print('model', m, flush=True)
