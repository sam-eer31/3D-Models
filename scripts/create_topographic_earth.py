import os
import urllib.request
import numpy as np
import trimesh
from PIL import Image
from scipy.ndimage import gaussian_filter, distance_transform_edt

DIRECTORY = os.path.dirname(os.path.abspath(__file__))
TEXTURES_DIR = os.path.join(DIRECTORY, "textures")
OUTPUT_DIR = os.path.abspath(os.path.join(DIRECTORY, "..", "output"))
os.makedirs(TEXTURES_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


def get_unique_output_path(base_name="topographic_earth.glb"):
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


NASA_ELEV_URL = "https://assets.science.nasa.gov/content/dam/science/esd/eo/images/bmng/topography/gebco_08_rev_elev_5400x2700.jpg"
NASA_BATH_URL = "https://assets.science.nasa.gov/content/dam/science/esd/eo/images/bmng/bathymetry/gebco_08_rev_bath_5400x2700.jpg"

def download_if_missing(filepath, url, name):
    if not os.path.exists(filepath):
        print(f"Downloading High-Res {name}...")
        urllib.request.urlretrieve(url, filepath)

def generate_multi_scale_normal_map(elevations_2d, out_path, strength=22.0):
    print("Generating High-Definition Normal Map...")
    elev_macro = gaussian_filter(elevations_2d, sigma=1.5)
    dy_macro, dx_macro = np.gradient(elev_macro)
    dy_micro, dx_micro = np.gradient(elevations_2d)
    
    dx = dx_macro * 0.3 + dx_micro * 0.7
    dy = dy_macro * 0.3 + dy_micro * 0.7
    
    normals = np.zeros((*elevations_2d.shape, 3), dtype=np.float32)
    normals[..., 0] = -dx * strength
    normals[..., 1] = dy * strength
    normals[..., 2] = 1.0
    norm = np.linalg.norm(normals, axis=2, keepdims=True)
    normals = normals / np.maximum(norm, 1e-6)
    normals = np.nan_to_num(normals, nan=0.0)
    normals = ((normals + 1.0) / 2.0 * 255.0).astype(np.uint8)
    
    img_out = Image.fromarray(normals, 'RGB')
    img_out.save(out_path, quality=92)
    return img_out

def compute_hillshade(elevations_2d, azimuth=315.0, altitude=45.0, exaggeration_factor=45.0):
    print("Computing Surface Relief Hillshade...")
    az_rad = np.radians(azimuth)
    alt_rad = np.radians(altitude)
    
    dy, dx = np.gradient(elevations_2d * exaggeration_factor)
    slope = np.arctan(np.hypot(dx, dy))
    aspect = np.arctan2(-dy, dx)
    
    shade = (np.sin(alt_rad) * np.cos(slope) + 
             np.cos(alt_rad) * np.sin(slope) * np.cos(az_rad - aspect))
    return np.nan_to_num(np.clip(shade, 0.0, 1.0), nan=0.5)

def generate_procedural_color_map(elevations_2d, water_arr, hillshade, out_path):
    print("Generating Procedural Hypsometric Color Texture...")
    h, w = elevations_2d.shape
    sea_depth = np.clip(-elevations_2d / 1.25, 0.0, 1.0)
    
    c_shallow = np.array([45.0, 215.0, 225.0])   # Aquamarine Shallow Reef
    c_shelf   = np.array([16.0, 135.0, 175.0])   # Coastal Continental Shelf
    c_deep    = np.array([8.0, 42.0, 130.0])     # Deep Ocean Blue
    c_trench  = np.array([2.0, 8.0, 40.0])       # Trench Navy
    
    water_rgb = np.zeros((h, w, 3), dtype=np.float32)
    
    mask0 = sea_depth <= 0.12
    t0 = np.clip(sea_depth / 0.12, 0.0, 1.0)[..., None]
    water_rgb = np.where(mask0[..., None], c_shallow * (1 - t0) + c_shelf * t0, water_rgb)
    
    mask1 = (sea_depth > 0.12) & (sea_depth <= 0.50)
    t1 = np.clip((sea_depth - 0.12) / 0.38, 0.0, 1.0)[..., None]
    water_rgb = np.where(mask1[..., None], c_shelf * (1 - t1) + c_deep * t1, water_rgb)
    
    mask2 = sea_depth > 0.50
    t2 = np.clip((sea_depth - 0.50) / 0.50, 0.0, 1.0)[..., None]
    water_rgb = np.where(mask2[..., None], c_deep * (1 - t2) + c_trench * t2, water_rgb)
    
    land_height = np.clip(elevations_2d, 0.0, 1.0)
    
    c_beach    = np.array([228.0, 202.0, 145.0])  # Warm Sand
    c_lowland  = np.array([40.0, 138.0, 46.0])    # Forest Green
    c_highland = np.array([148.0, 108.0, 42.0])   # Highland Ochre
    c_rock     = np.array([122.0, 118.0, 112.0])  # Slate Grey
    c_snow     = np.array([250.0, 252.0, 255.0])  # Summit Snow
    
    land_rgb = np.zeros((h, w, 3), dtype=np.float32)
    
    l_mask0 = land_height <= 0.025
    lt0 = np.clip(land_height / 0.025, 0.0, 1.0)[..., None]
    land_rgb = np.where(l_mask0[..., None], c_beach * (1 - lt0) + c_lowland * lt0, land_rgb)
    
    l_mask1 = (land_height > 0.025) & (land_height <= 0.30)
    lt1 = np.clip((land_height - 0.025) / 0.275, 0.0, 1.0)[..., None]
    land_rgb = np.where(l_mask1[..., None], c_lowland * (1 - lt1) + c_highland * lt1, land_rgb)
    
    l_mask2 = (land_height > 0.30) & (land_height <= 0.62)
    lt2 = np.clip((land_height - 0.30) / 0.32, 0.0, 1.0)[..., None]
    land_rgb = np.where(l_mask2[..., None], c_highland * (1 - lt2) + c_rock * lt2, land_rgb)
    
    l_mask3 = land_height > 0.62
    lt3 = np.clip((land_height - 0.62) / 0.38, 0.0, 1.0)[..., None]
    land_rgb = np.where(l_mask3[..., None], c_rock * (1 - lt3) + c_snow * lt3, land_rgb)
    
    final_rgb = np.where(water_arr[..., None], water_rgb, land_rgb)
    shade_factor = (0.68 + 0.45 * hillshade)[..., None]
    final_rgb = final_rgb * shade_factor
    
    final_rgb = np.nan_to_num(np.clip(final_rgb, 0.0, 255.0), nan=128.0).astype(np.uint8)
    
    img_out = Image.fromarray(np.flip(final_rgb, axis=1), 'RGB')
    img_out.save(out_path, quality=92)
    return img_out

def smooth_coastal_transition(land_elev, sea_elev, water_mask, blend_radius=10.0):
    print("Applying Smooth Coastal Distance Transition...")
    dist_into_water = distance_transform_edt(water_mask)
    dist_into_land = distance_transform_edt(~water_mask)
    
    t_water = np.clip(dist_into_water / blend_radius, 0.0, 1.0)
    s_water = 3.0 * (t_water ** 2) - 2.0 * (t_water ** 3)
    
    t_land = np.clip(dist_into_land / blend_radius, 0.0, 1.0)
    s_land = 3.0 * (t_land ** 2) - 2.0 * (t_land ** 3)
    
    sea_elev_smooth = sea_elev * s_water
    land_elev_smooth = land_elev * s_land
    
    elevations = np.where(water_mask, sea_elev_smooth, land_elev_smooth)
    return np.nan_to_num(elevations, nan=0.0)

def process_high_detail_heights(topo_img, bathy_img, water_img, target_size=(4096, 2048)):
    print(f"Processing Topography & Bathymetry Data at {target_size[0]}x{target_size[1]}...")
    w, h = target_size
    t_img = topo_img.resize((w, h), Image.Resampling.LANCZOS)
    b_img = bathy_img.resize((w, h), Image.Resampling.LANCZOS)
    w_img = water_img.resize((w, h), Image.Resampling.NEAREST)
    
    topo_raw = np.flip(np.array(t_img.convert('L'), dtype=np.float32), axis=1) / 255.0
    bathy_raw = np.flip(np.array(b_img.convert('L'), dtype=np.float32), axis=1) / 255.0
    water_mask = np.flip(np.array(w_img.convert('L')), axis=1) > 128
    
    topo_base = gaussian_filter(topo_raw, sigma=0.8)
    bathy_base = gaussian_filter(bathy_raw, sigma=0.8)
    
    topo_detail = topo_raw - topo_base
    bathy_detail = bathy_raw - bathy_base
    
    topo_enhanced = topo_base + 2.0 * topo_detail
    bathy_enhanced = bathy_base + 1.6 * bathy_detail
    
    land_elev = np.clip(topo_enhanced, 0.0, 1.25)
    sea_elev = - (1.0 - np.clip(bathy_enhanced, 0.0, 1.0)) * 1.25
    
    elevations = smooth_coastal_transition(land_elev, sea_elev, water_mask, blend_radius=10.0)
    return np.nan_to_num(elevations, nan=0.0), water_mask

def create_exaggerated_sphere(radius, elevations_map, exaggeration=0.07, segments=1024):
    print(f"Resampling heightmap to {segments}x{segments} vertex mesh grid...")
    
    grid_w, grid_h = segments + 1, segments + 1
    img_f = Image.fromarray(elevations_map.astype(np.float32), mode='F')
    res_f = img_f.resize((grid_w, grid_h), Image.Resampling.LANCZOS)
    elev_resampled = np.nan_to_num(np.array(res_f, dtype=np.float32), nan=0.0)
    
    u = np.linspace(0, 1, segments + 1)
    v = np.linspace(0, 1, segments + 1)
    U, V = np.meshgrid(u, v)
    
    phi = (0.5 - V) * np.pi
    theta = U * 2.0 * np.pi
    
    r = radius + (elev_resampled * exaggeration)
    
    print("Calculating 3D vertex positions...")
    y = r * np.sin(phi)
    x = r * np.cos(phi) * np.cos(theta)
    z = r * np.cos(phi) * np.sin(theta)
    
    vertices = np.stack([x.flatten(), y.flatten(), z.flatten()], axis=1)
    vertices = np.nan_to_num(vertices, nan=0.0)
    uvs = np.stack([1.0 - U.flatten(), 1.0 - V.flatten()], axis=1)
    uvs = np.nan_to_num(uvs, nan=0.0)
    
    print("Generating quad mesh faces...")
    i = np.arange(segments)
    j = np.arange(segments)
    I, J = np.meshgrid(i, j, indexing='ij')
    
    v1 = I * (segments + 1) + J
    v2 = v1 + 1
    v3 = (I + 1) * (segments + 1) + J
    v4 = v3 + 1
    
    f1 = np.stack([v1.flatten(), v2.flatten(), v3.flatten()], axis=1)
    f2 = np.stack([v2.flatten(), v4.flatten(), v3.flatten()], axis=1)
    faces = np.vstack([f1.reshape(-1, 3), f2.reshape(-1, 3)])
    
    print("Building trimesh geometry...")
    mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
    mesh.visual = trimesh.visual.TextureVisuals(uv=uvs)
    
    _ = mesh.vertex_normals
    if np.isnan(mesh.vertex_normals).any():
        mesh.vertex_normals = np.nan_to_num(mesh.vertex_normals, nan=0.0)
        
    return mesh

def build_model():
    print("Preparing high-resolution datasets...")
    topomap_path = os.path.join(TEXTURES_DIR, "earth_elevation.jpg")
    bathymap_path = os.path.join(TEXTURES_DIR, "earth_bathymetry.jpg")
    watermap_path = os.path.join(TEXTURES_DIR, "earth-water.png")
    
    download_if_missing(topomap_path, NASA_ELEV_URL, "Topography (5.4K)")
    download_if_missing(bathymap_path, NASA_BATH_URL, "Bathymetry (5.4K)")
    
    if not os.path.exists(watermap_path):
        print("Error: earth-water.png missing. Please run create_earth.py first.")
        return

    topomap = Image.open(topomap_path)
    bathymap = Image.open(bathymap_path)
    watermap = Image.open(watermap_path)
    
    # Process heightmap at 4096x2048 resolution
    elevations_2d, water_mask = process_high_detail_heights(topomap, bathymap, watermap, target_size=(4096, 2048))
    
    # 2. Generate JPEG-compressed Normal Map
    normal_path = os.path.join(TEXTURES_DIR, "earth_exaggerated_normal.jpg")
    normal_img = generate_multi_scale_normal_map(elevations_2d, normal_path, strength=22.0)
    
    # 3. Compute Hillshade
    hillshade = compute_hillshade(elevations_2d, azimuth=315.0, altitude=45.0, exaggeration_factor=45.0)
        
    # 4. Generate JPEG-compressed Color Map
    color_map_path = os.path.join(TEXTURES_DIR, "earth_procedural_colormap.jpg")
    base_color_img = generate_procedural_color_map(elevations_2d, water_mask, hillshade, color_map_path)
    
    # 5. Generate Metallic/Roughness Map
    pbr_path = os.path.join(TEXTURES_DIR, "earth_exaggerated_pbr.jpg")
    w, h = (4096, 2048)
    pbr_arr = np.zeros((h, w, 3), dtype=np.uint8)
    w_arr = np.array(watermap.convert('L').resize((w, h), Image.Resampling.NEAREST)) > 128
    pbr_arr[..., 1] = np.where(w_arr, 25, 225).astype(np.uint8)
    Image.fromarray(pbr_arr, 'RGB').save(pbr_path, quality=90)
    pbr_img = Image.open(pbr_path)
        
    # 6. Generate 1024-segment sphere mesh (2 million polygons)
    segments = 1024
    exaggeration = 0.07
    
    mesh = create_exaggerated_sphere(1.0, elevations_2d, exaggeration=exaggeration, segments=segments)
    
    print("Applying High-Quality PBR Material...")
    mat = trimesh.visual.material.PBRMaterial(
        baseColorTexture=base_color_img,
        normalTexture=normal_img,
        metallicRoughnessTexture=pbr_img,
        roughnessFactor=1.0,
        metallicFactor=0.0
    )
    mesh.visual.material = mat
    
    scene = trimesh.Scene()
    scene.add_geometry(mesh, node_name="EarthTerrain")
    
    # Single clean output GLB model in output directory
    out_file = get_unique_output_path("topographic_earth.glb")
    print(f"Exporting clean GLB model to {out_file}...")
    scene.export(out_file)
    
    file_size_mb = os.path.getsize(out_file) / (1024 * 1024)
    print(f"\n=========================================")
    print(f"Success! High-Quality Clean Earth GLB model generated.")
    print(f"Output Model: {out_file} ({file_size_mb:.1f} MB)")
    print("=========================================\n")

if __name__ == "__main__":
    build_model()
