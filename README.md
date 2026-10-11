# 3D Celestial Models Generator & Optimizer

High-fidelity procedural 3D model generator for astronomical bodies (Earth, Moon, Topographic Relief Earth) and automated GLB/GLTF compression pipeline.

## Features

- **Earth (`create_earth.py`)**: Multi-layered Earth model with day surface textures, cloud layers, and city night lights.
- **Topographic Earth (`create_topographic_earth.py`)**: Elevation-exaggerated relief model using NASA GEBCO elevation and bathymetry data.
- **Moon (`create_moon.py`)**: High-resolution lunar surface using 8K imagery with bump mapping.
- **Model Compressor (`compressor/`)**: Automated texture optimization (WebP conversion, Meshopt, and deduplication) using Khronos `@gltf-transform/cli`.

---

## Directory Structure

```text
3D-Models/
├── build_model.bat            # Main interactive launcher for model creation
├── compressor/
│   ├── compress_model.bat     # Interactive batch compressor
│   └── compress_model.py      # GLTF/GLB optimization engine
├── output/                    # Generated 3D models saved here (.glb)
└── scripts/
    ├── run_generator.py       # Script runner and batch generator
    ├── create_earth.py        # Layered animated Earth script
    ├── create_moon.py         # 8K Moon script
    ├── create_topographic_earth.py # Exaggerated topographic Earth script
    └── textures/              # Texture assets cache
```

---

## Getting Started

### Prerequisites

- **Python 3.10+** with required packages:
  ```bash
  pip install trimesh pillow numpy pygltflib requests scipy
  ```
- **Node.js / npx** (for running the GLB compressor via `@gltf-transform/cli`).

### Generating 3D Models

Double-click `build_model.bat` in the root folder, or run:
```bash
python scripts/run_generator.py
```
Select an individual model to generate (1 by 1) or choose the option to generate all models at once. After each run, you can choose to build more models or cleanly exit. Generated files are automatically saved into `output/` with duplicate-numbering protection (e.g. `earth.glb`, `earth_1.glb`).

### Compressing 3D Models

To compress any generated model in `output/`:
1. Run `compressor/compress_model.bat`
2. Select the model from the interactive list, or drag and drop a file onto the script.
3. The compressed model will be saved as `<model_name>_compressed.glb` in `output/`.

---

## License

This project is licensed under the terms of the MIT license. See [LICENSE](LICENSE) for details.
