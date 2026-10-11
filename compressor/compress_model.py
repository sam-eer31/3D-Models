import os
import sys
import subprocess
import shutil

DIRECTORY = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(DIRECTORY, ".."))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
MODELS_DIR = OUTPUT_DIR if os.path.isdir(OUTPUT_DIR) else DIRECTORY


def get_input_file():
    # If passed as command line argument (e.g. via drag-and-drop or CLI)
    if len(sys.argv) > 1:
        target = sys.argv[1].strip().strip('"').strip("'")
        if not os.path.isabs(target):
            if os.path.exists(os.path.join(MODELS_DIR, target)):
                target = os.path.join(MODELS_DIR, target)
            else:
                target = os.path.join(DIRECTORY, target)
        return target

    print("===================================================")
    print("           3D GLB / GLTF Model Compressor          ")
    print("===================================================\n")

    # Find available 3D models in MODELS_DIR (output folder)
    candidates = []
    if os.path.exists(MODELS_DIR):
        candidates = [
            f for f in sorted(os.listdir(MODELS_DIR))
            if f.lower().endswith((".glb", ".gltf")) and not f.lower().endswith(("_compressed.glb", "_compressed.gltf"))
        ]

    # Also check DIRECTORY if models exist there
    if os.path.exists(DIRECTORY) and DIRECTORY != MODELS_DIR:
        local_cand = [
            f for f in sorted(os.listdir(DIRECTORY))
            if f.lower().endswith((".glb", ".gltf")) and not f.lower().endswith(("_compressed.glb", "_compressed.gltf"))
        ]
        for c in local_cand:
            if c not in candidates:
                candidates.append(c)

    if candidates:
        folder_display = os.path.basename(MODELS_DIR) if os.path.exists(MODELS_DIR) else "current directory"
        print(f"Available models (in '{folder_display}'):")
        for idx, filename in enumerate(candidates, 1):
            file_path = os.path.join(MODELS_DIR, filename) if os.path.exists(os.path.join(MODELS_DIR, filename)) else os.path.join(DIRECTORY, filename)
            size_mb = os.path.getsize(file_path) / (1024 * 1024)
            print(f"  [{idx}] {filename} ({size_mb:.2f} MB)")
        print()

    prompt = "Enter model filename, path, or number from list: "
    user_input = input(prompt).strip().strip('"').strip("'")

    if not user_input:
        if candidates:
            first_file = candidates[0]
            return os.path.join(MODELS_DIR, first_file) if os.path.exists(os.path.join(MODELS_DIR, first_file)) else os.path.join(DIRECTORY, first_file)
        print("Error: No file specified.")
        sys.exit(1)

    # 1. Number selection from list
    if user_input.isdigit() and candidates:
        idx = int(user_input)
        if 1 <= idx <= len(candidates):
            chosen = candidates[idx - 1]
            return os.path.join(MODELS_DIR, chosen) if os.path.exists(os.path.join(MODELS_DIR, chosen)) else os.path.join(DIRECTORY, chosen)

    # 2. Check if user typed or dragged an exact file or absolute path
    if os.path.isabs(user_input) and os.path.exists(user_input):
        return user_input

    # Check MODELS_DIR first, then DIRECTORY
    for search_dir in [MODELS_DIR, DIRECTORY]:
        direct_path = os.path.join(search_dir, user_input)
        if os.path.exists(direct_path):
            return direct_path
        for ext in [".glb", ".gltf"]:
            if os.path.exists(direct_path + ext):
                return direct_path + ext

    # 3. Flexible match (e.g. 'earth relief' -> 'earth_relief.glb')
    clean_input = user_input.lower().replace(" ", "").replace("_", "").replace("-", "")
    for cand in candidates:
        cand_clean = os.path.splitext(cand)[0].lower().replace(" ", "").replace("_", "").replace("-", "")
        if clean_input == cand_clean or clean_input in cand_clean:
            return os.path.join(MODELS_DIR, cand) if os.path.exists(os.path.join(MODELS_DIR, cand)) else os.path.join(DIRECTORY, cand)

    return os.path.join(MODELS_DIR, user_input)


def get_output_file(input_file):
    dirname, filename = os.path.split(input_file)
    stem, ext = os.path.splitext(filename)
    output_filename = f"{stem}_compressed{ext}"
    if os.path.isdir(OUTPUT_DIR):
        return os.path.join(OUTPUT_DIR, output_filename)
    return os.path.join(dirname, output_filename)


def compress_model():
    input_file = get_input_file()

    if not os.path.exists(input_file):
        print(f"\nError: Could not find '{input_file}'.")
        sys.exit(1)

    output_file = get_output_file(input_file)
    model_name = os.path.basename(input_file)
    output_name = os.path.basename(output_file)

    initial_size_mb = os.path.getsize(input_file) / (1024 * 1024)
    print(f"\n[1/1] Processing Selected Model:")
    print(f"  Input:  {model_name} ({initial_size_mb:.2f} MB)")
    print(f"  Output: {output_name}")
    print("\nCompressing geometry & textures (WebP + Meshopt + Deduplication)...")
    print("Please wait, this may take a moment...\n")

    cmd = f'npx -y @gltf-transform/cli optimize "{input_file}" "{output_file}" --texture-compress webp'

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
        if result.returncode != 0:
            print("Warning / Output log:")
            print(result.stderr or result.stdout)
    except Exception as e:
        print(f"Error executing compression process: {e}")
        sys.exit(1)

    if os.path.exists(output_file):
        compressed_size_mb = os.path.getsize(output_file) / (1024 * 1024)
        saved_pct = ((initial_size_mb - compressed_size_mb) / initial_size_mb) * 100.0

        print("\n===================================================")
        print("SUCCESS! Model Compressed Successfully.")
        print(f"Original Size:   {initial_size_mb:.2f} MB")
        print(f"Compressed Size: {compressed_size_mb:.2f} MB")
        print(f"Size Reduction:  {saved_pct:.1f}% Smaller!")
        print(f"Saved To:        {output_file}")
        print("===================================================\n")
    else:
        print("\nError: Compressed output file was not created.")
        sys.exit(1)


if __name__ == "__main__":
    compress_model()

