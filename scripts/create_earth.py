import os
import requests
import numpy as np
import trimesh
from PIL import Image, ImageFilter
import pygltflib
import struct
import math

DIRECTORY = os.path.dirname(os.path.abspath(__file__))
TEXTURES_DIR = os.path.join(DIRECTORY, "textures")
OUTPUT_DIR = os.path.abspath(os.path.join(DIRECTORY, "..", "output"))
os.makedirs(TEXTURES_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


def get_unique_output_path(base_name="earth.glb"):
    stem, ext = os.path.splitext(base_name)
    target = os.path.join(OUTPUT_DIR, base_name)
    if not os.path.exists(target):
        return target
    counter = 1
    while True:
        target = os.path.join(OUTPUT_DIR, f"{stem}_{counter}{ext}")
        if not os.path.exists(target):
            return target
        counter += 1


REMOTE_TEXTURES = {
    "earth-topology.png": "https://unpkg.com/three-globe/example/img/earth-topology.png",
    "earth-water.png": "https://unpkg.com/three-globe/example/img/earth-water.png",
    "earth_lights.png": "https://raw.githubusercontent.com/mrdoob/three.js/master/examples/textures/planets/earth_lights_2048.png"
}

def download_missing_textures():
    for filename, url in REMOTE_TEXTURES.items():
        filepath = os.path.join(TEXTURES_DIR, filename)
        if not os.path.exists(filepath):
            print(f"Downloading {filename}...")
            response = requests.get(url, stream=True)
            response.raise_for_status()
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

def create_textured_sphere(radius, segments=128, y_scale=1.0):
    u = np.linspace(0, 1, segments + 1)
    v = np.linspace(0, 1, segments + 1)
    U, V = np.meshgrid(u, v)
    
    phi = (0.5 - V) * np.pi
    theta = U * 2 * np.pi
    
    y = radius * np.sin(phi) * y_scale
    x = radius * np.cos(phi) * np.cos(theta)
    z = radius * np.cos(phi) * np.sin(theta)
    
    vertices = np.stack([x.flatten(), y.flatten(), z.flatten()], axis=1)
    uvs = np.stack([1.0 - U.flatten(), 1.0 - V.flatten()], axis=1)
    
    normals = np.stack([x.flatten()/radius, y.flatten()/radius, z.flatten()/radius], axis=1)
    normals = normals / np.linalg.norm(normals, axis=1, keepdims=True)
    
    faces = []
    for i in range(segments):
        for j in range(segments):
            v1 = i * (segments + 1) + j
            v2 = v1 + 1
            v3 = (i + 1) * (segments + 1) + j
            v4 = v3 + 1
            faces.append([v1, v2, v3])
            faces.append([v2, v4, v3])
            
    mesh = trimesh.Trimesh(vertices=vertices, faces=faces, vertex_normals=normals, process=False)
    mesh.visual = trimesh.visual.TextureVisuals(uv=uvs)
    return mesh


def generate_bump_to_normal(bump_img):
    out_path = os.path.join(TEXTURES_DIR, "earth_normal_generated.png")
    if os.path.exists(out_path): return Image.open(out_path)
    img = bump_img.convert('L')
    img_array = np.array(img, dtype=np.float32) / 255.0
    dy, dx = np.gradient(img_array)
    normals = np.zeros((*img_array.shape, 3), dtype=np.float32)
    normals[..., 0] = -dx * 15.0 
    normals[..., 1] = dy * 15.0
    normals[..., 2] = 1.0
    n = np.linalg.norm(normals, axis=2, keepdims=True)
    normals = normals / n
    normals = ((normals + 1.0) / 2.0 * 255).astype(np.uint8)
    img_out = Image.fromarray(normals, 'RGB')
    img_out.save(out_path) 
    return img_out

def build_model():
    download_missing_textures()
    
    daymap = Image.open(os.path.join(TEXTURES_DIR, "8k_earth_daymap.jpg"))
    cloudsmap = Image.open(os.path.join(TEXTURES_DIR, "8k_earth_clouds.jpg"))
    bumpmap = Image.open(os.path.join(TEXTURES_DIR, "earth-topology.png"))
    watermap = Image.open(os.path.join(TEXTURES_DIR, "earth-water.png"))
    lightsmap = Image.open(os.path.join(TEXTURES_DIR, "earth_lights.png"))

    normal_map = generate_bump_to_normal(bumpmap)
    
    pbr_path = os.path.join(TEXTURES_DIR, "earth_mr_generated.png")
    w, h = watermap.size
    pbr_map = np.zeros((h, w, 4), dtype=np.uint8)
    water_array = np.array(watermap.convert('L'))
    
    # Realistic Water Reflections (Standard PBR):
    # Green (Roughness): Land is 255 (rough), Water is 25 (very smooth, sharp reflections)
    pbr_map[..., 1] = 255 - (water_array * 0.9).astype(np.uint8)
    # Blue (Metallic): Land is 0, Water is 0 (water is a dielectric, not a metal)
    pbr_map[..., 2] = 0
    pbr_map[..., 3] = 255
    Image.fromarray(pbr_map, 'RGBA').save(pbr_path)
    
    pbr_image = Image.open(pbr_path)
    
    day_w, day_h = daymap.size
    watermap_resized = watermap.resize((day_w, day_h))
    water_array = np.array(watermap_resized.convert('L'))
    
    water_rgba_path = os.path.join(TEXTURES_DIR, "earth_water_rgba.png")
    if not os.path.exists(water_rgba_path):
        print("Generating Water RGBA mask...")
        day_array = np.array(daymap.convert('RGB'))
        w_rgba = np.zeros((*day_array.shape[:2], 4), dtype=np.uint8)
        w_rgba[..., :3] = day_array
        w_rgba[..., 3] = water_array
        Image.fromarray(w_rgba, 'RGBA').save(water_rgba_path)
    water_rgba = Image.open(water_rgba_path)
    
    land_rgba_path = os.path.join(TEXTURES_DIR, "earth_land_rgba.png")
    if not os.path.exists(land_rgba_path):
        print("Generating Land RGBA mask...")
        day_array = np.array(daymap.convert('RGB'))
        l_rgba = np.zeros((*day_array.shape[:2], 4), dtype=np.uint8)
        l_rgba[..., :3] = day_array
        l_rgba[..., 3] = 255 - water_array
        Image.fromarray(l_rgba, 'RGBA').save(land_rgba_path)
    land_rgba = Image.open(land_rgba_path)
    
    lights_rgba_path = os.path.join(TEXTURES_DIR, "earth_lights_rgba.png")
    if not os.path.exists(lights_rgba_path):
        print("Generating Lights RGBA mask...")
        l_rgb = np.array(lightsmap.convert('RGB'))
        l_gray = np.array(lightsmap.convert('L'))
        l_rgba = np.zeros((*l_rgb.shape[:2], 4), dtype=np.uint8)
        l_rgba[..., :3] = l_rgb
        l_rgba[..., 3] = l_gray
        Image.fromarray(l_rgba, 'RGBA').save(lights_rgba_path)
    lights_rgba = Image.open(lights_rgba_path)
    
    clouds_rgba_path = os.path.join(TEXTURES_DIR, "earth_clouds_rgba.png")
    if not os.path.exists(clouds_rgba_path):
        c_gray = np.array(cloudsmap.convert('L'))
        c_rgba = np.zeros((*c_gray.shape, 4), dtype=np.uint8)
        c_rgba[..., 0] = 255; c_rgba[..., 1] = 255; c_rgba[..., 2] = 255; c_rgba[..., 3] = c_gray 
        Image.fromarray(c_rgba, 'RGBA').save(clouds_rgba_path)
    clouds_rgba = Image.open(clouds_rgba_path)
    
    print("Loading specialized internal rock/magma materials...")
    magma_map = Image.open(os.path.join(TEXTURES_DIR, "mantle_magma.png"))
    core_map = Image.open(os.path.join(TEXTURES_DIR, "inner_core.png"))
    outer_core_map = Image.open(os.path.join(TEXTURES_DIR, "outer_core.png"))
    crust_rock_map = Image.open(os.path.join(TEXTURES_DIR, "crust_rock.png"))
    
    scene = trimesh.Scene()
    
    # Material Definitions
    mat_core = trimesh.visual.material.PBRMaterial(baseColorTexture=core_map, emissiveTexture=core_map, emissiveFactor=[1.0, 1.0, 1.0])
    mat_outer_core = trimesh.visual.material.PBRMaterial(baseColorTexture=outer_core_map, emissiveTexture=outer_core_map, emissiveFactor=[1.0, 1.0, 1.0])
    mat_magma = trimesh.visual.material.PBRMaterial(baseColorTexture=magma_map, emissiveTexture=magma_map, emissiveFactor=[1.0, 1.0, 1.0])
    mat_rock = trimesh.visual.material.PBRMaterial(baseColorTexture=crust_rock_map, roughnessFactor=1.0)
    mat_water = trimesh.visual.material.PBRMaterial(
        baseColorTexture=water_rgba, metallicRoughnessTexture=pbr_image,
        normalTexture=normal_map, roughnessFactor=1.0, metallicFactor=1.0,
        alphaMode='MASK', alphaCutoff=0.5
    )
    mat_land = trimesh.visual.material.PBRMaterial(
        baseColorTexture=land_rgba, normalTexture=normal_map, 
        roughnessFactor=1.0, alphaMode='MASK', alphaCutoff=0.5
    )
    mat_lights = trimesh.visual.material.PBRMaterial(
        baseColorTexture=lights_rgba, emissiveTexture=lights_rgba,
        emissiveFactor=[1.0, 1.0, 1.0], alphaMode='BLEND'
    )
    mat_clouds = trimesh.visual.material.PBRMaterial(baseColorTexture=clouds_rgba, alphaMode='BLEND')

    print("Generating pure nested full spheres...")
    
    mesh_ic = create_textured_sphere(0.19, segments=64)
    mesh_ic.visual.material = mat_core
    scene.add_geometry(mesh_ic, node_name="InnerCore")
    
    mesh_oc = create_textured_sphere(0.546, segments=64)
    mesh_oc.visual.material = mat_outer_core
    scene.add_geometry(mesh_oc, node_name="OuterCore")
    
    mesh_mantle = create_textured_sphere(0.990, segments=128)
    mesh_mantle.visual.material = mat_magma
    scene.add_geometry(mesh_mantle, node_name="Mantle")
    
    mesh_rock = create_textured_sphere(0.999, segments=128)
    mesh_rock.visual.material = mat_rock
    scene.add_geometry(mesh_rock, node_name="CrustRock")
    
    mesh_water = create_textured_sphere(1.0, segments=128)
    mesh_water.visual.material = mat_water
    scene.add_geometry(mesh_water, node_name="Water")
    
    mesh_land = create_textured_sphere(1.0005, segments=128)
    mesh_land.visual.material = mat_land
    scene.add_geometry(mesh_land, node_name="Land")
    
    mesh_lights = create_textured_sphere(1.001, segments=128)
    mesh_lights.visual.material = mat_lights
    scene.add_geometry(mesh_lights, node_name="CityLights")
    
    mesh_clouds = create_textured_sphere(1.0025, segments=128)
    mesh_clouds.visual.material = mat_clouds
    scene.add_geometry(mesh_clouds, node_name="Clouds")
    
    out_file = get_unique_output_path("earth.glb")
    print("Baking GLB binary file...")
    scene.export(out_file)
    
    print("Injecting complex PBR parameters via pygltflib...")
    gltf = pygltflib.GLTF2().load(out_file)
    for mat in gltf.materials:
        mat.extensions = mat.extensions or {}
        mat.extensions["KHR_materials_ior"] = {"ior": 1.5}
        if mat.name and "crust" in mat.name.lower():
            mat.extensions["KHR_materials_clearcoat"] = {"clearcoatFactor": 0.5, "clearcoatRoughnessFactor": 0.2}
            
    print("Injecting GLTF Binary Animations...")
    world_node = 0
    clouds_node = None
    for i, n in enumerate(gltf.nodes):
        if n.name == "Clouds":
            clouds_node = i
            break
            
    if clouds_node is not None:
        def euler_to_quat(y_deg):
            rad = math.radians(y_deg)
            return [0.0, math.sin(rad/2), 0.0, math.cos(rad/2)]
            
        degrees = [0, 90, 180, 270, 360]
        times_earth = [0.0, 15.0, 30.0, 45.0, 60.0]
        quats_earth = []
        for d in degrees: quats_earth.extend(euler_to_quat(d))
        
        times_clouds = [0.0, 75.0, 150.0, 225.0, 300.0]
        quats_clouds = []
        for d in degrees: quats_clouds.extend(euler_to_quat(d))
        
        blob = bytearray(gltf._glb_data) if gltf._glb_data else bytearray()
        while len(blob) % 4 != 0: blob.append(0)
            
        def add_accessor(data_bytes, componentType, count, type_str):
            byteOffset = len(blob)
            blob.extend(data_bytes)
            byteLength = len(data_bytes)
            while len(blob) % 4 != 0: blob.append(0)
                
            gltf.bufferViews.append(pygltflib.BufferView(buffer=0, byteOffset=byteOffset, byteLength=byteLength))
            bv_idx = len(gltf.bufferViews) - 1
            
            gltf.accessors.append(pygltflib.Accessor(bufferView=bv_idx, componentType=componentType, count=count, type=type_str))
            return len(gltf.accessors) - 1
            
        acc_earth_time = add_accessor(struct.pack(f"<{len(times_earth)}f", *times_earth), pygltflib.FLOAT, len(times_earth), pygltflib.SCALAR)
        acc_earth_rot = add_accessor(struct.pack(f"<{len(quats_earth)}f", *quats_earth), pygltflib.FLOAT, len(times_earth), pygltflib.VEC4)
        
        acc_clouds_time = add_accessor(struct.pack(f"<{len(times_clouds)}f", *times_clouds), pygltflib.FLOAT, len(times_clouds), pygltflib.SCALAR)
        acc_clouds_rot = add_accessor(struct.pack(f"<{len(quats_clouds)}f", *quats_clouds), pygltflib.FLOAT, len(times_clouds), pygltflib.VEC4)
        
        anim = pygltflib.Animation(name="Earth Spin & Cloud Drift Cycle")
        anim.samplers.append(pygltflib.AnimationSampler(input=acc_earth_time, output=acc_earth_rot, interpolation=pygltflib.LINEAR))
        anim.channels.append(pygltflib.AnimationChannel(sampler=0, target=pygltflib.AnimationChannelTarget(node=world_node, path=pygltflib.ROTATION)))
        
        anim.samplers.append(pygltflib.AnimationSampler(input=acc_clouds_time, output=acc_clouds_rot, interpolation=pygltflib.LINEAR))
        anim.channels.append(pygltflib.AnimationChannel(sampler=1, target=pygltflib.AnimationChannelTarget(node=clouds_node, path=pygltflib.ROTATION)))
        
        gltf.animations.append(anim)
        gltf.buffers[0].byteLength = len(blob)
        gltf.set_binary_blob(bytes(blob))

    gltf.save(out_file)
    
    print(f"\n=========================================")
    print("Success! Perfect layered Earth model generated.")
    print(f"Saved to: {out_file}")
    print("=========================================\n")

if __name__ == "__main__":
    build_model()
