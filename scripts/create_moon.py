import os
import requests
import numpy as np
import trimesh
from PIL import Image

DIRECTORY = os.path.dirname(os.path.abspath(__file__))
TEXTURES_DIR = os.path.join(DIRECTORY, "textures")
OUTPUT_DIR = os.path.abspath(os.path.join(DIRECTORY, "..", "output"))
os.makedirs(TEXTURES_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


def get_unique_output_path(base_name="moon.glb"):
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


MOON_URL = "https://www.solarsystemscope.com/textures/download/8k_moon.jpg"

def download_moon_texture():
    filepath = os.path.join(TEXTURES_DIR, "8k_moon.jpg")
    if not os.path.exists(filepath):
        print(f"Downloading 8k_moon.jpg...")
        response = requests.get(MOON_URL, stream=True)
        response.raise_for_status()
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
    return filepath

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
    
    normals = np.stack([x.flatten()/radius, y.flatten()/(radius*y_scale), z.flatten()/radius], axis=1)
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

def download_and_create_normal_map():
    filepath_height = os.path.join(TEXTURES_DIR, "ldem_3_8bit.jpg")
    filepath_normal = os.path.join(TEXTURES_DIR, "moon_normal.jpg")
    
    # Return immediately if normal map already exists
    if os.path.exists(filepath_normal):
        return filepath_normal

    BUMP_URL = "https://svs.gsfc.nasa.gov/vis/a000000/a004700/a004720/ldem_3_8bit.jpg"
    
    if not os.path.exists(filepath_height):
        try:
            print("Downloading displacement map from NASA SVS...")
            response = requests.get(BUMP_URL, stream=True, timeout=5)
            response.raise_for_status()
            with open(filepath_height, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
        except Exception as e:
            print(f"NASA server unreachable ({e}). Generating normal map from 8k_moon.jpg...")

    print("Generating normal map...")
    source_path = filepath_height if os.path.exists(filepath_height) else os.path.join(TEXTURES_DIR, "8k_moon.jpg")
    img = Image.open(source_path).convert('L')
    if img.size[0] > 4096:
        img = img.resize((4096, 2048), Image.Resampling.LANCZOS)
    
    from PIL import ImageFilter
    print("Smoothing heightmap for photorealism...")
    img = img.filter(ImageFilter.GaussianBlur(radius=2))
    img_arr = np.array(img, dtype=np.float32) / 255.0
    
    # Calculate gradients
    dzdy, dzdx = np.gradient(img_arr)
    strength = 3.0
    dzdx *= strength
    dzdy *= strength
    
    # Add micro-noise to simulate dusty soil/regolith particles
    print("Adding micro-roughness for dusty soil effect...")
    dust_strength = 0.15
    noise_x = np.random.normal(0, dust_strength, size=img_arr.shape).astype(np.float32)
    noise_y = np.random.normal(0, dust_strength, size=img_arr.shape).astype(np.float32)
    
    dzdx += noise_x
    dzdy += noise_y
    
    normal_map = np.empty((img_arr.shape[0], img_arr.shape[1], 3), dtype=np.float32)
    normal_map[..., 0] = -dzdx
    normal_map[..., 1] = dzdy
    normal_map[..., 2] = 1.0
    
    norm = np.linalg.norm(normal_map, axis=2, keepdims=True)
    normal_map = normal_map / norm
    
    normal_map = ((normal_map + 1.0) * 127.5).astype(np.uint8)
    Image.fromarray(normal_map).save(filepath_normal, quality=90)
    
    return filepath_normal

def build_moon():
    img_path = download_moon_texture()
    normal_path = download_and_create_normal_map()
    
    print("Loading Moon material...")
    moon_map = Image.open(img_path)
    normal_map_img = Image.open(normal_path)
    mat_moon = trimesh.visual.material.PBRMaterial(
        baseColorTexture=moon_map,
        normalTexture=normal_map_img,
        roughnessFactor=1.0,
        metallicFactor=0.0
    )

    print("Generating pure moon sphere...")
    scene = trimesh.Scene()
    
    # Accurate mathematical scale and oblateness
    # FIX 4: Increased segments to 1024 to fix the jagged shadow terminator and polygonal edges (the "Terminator Problem")
    mesh_moon = create_textured_sphere(0.2727, segments=1024, y_scale=0.9988)
    mesh_moon.visual.material = mat_moon
    
    # We leave the moon at [0,0,0] as requested for the standalone file
    scene.add_geometry(mesh_moon, node_name="Moon")
    
    out_file = get_unique_output_path("moon.glb")
    print("Baking GLB binary file...")
    scene.export(out_file)
    
    print(f"\n=========================================")
    print("Success! Perfect Moon model generated.")
    print(f"Saved to: {out_file}")
    print("=========================================\n")

if __name__ == "__main__":
    build_moon()
