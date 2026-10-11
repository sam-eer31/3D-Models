import os
import sys
import subprocess
import shutil

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(ROOT_DIR, "scripts")
OUTPUT_DIR = os.path.join(ROOT_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def get_available_scripts():
    if not os.path.isdir(SCRIPTS_DIR):
        return []
    return [
        f for f in sorted(os.listdir(SCRIPTS_DIR))
        if f.lower().endswith(".py") and not f.startswith(("_", "run_"))
    ]


def ensure_unique_destination(output_dir, filename):
    stem, ext = os.path.splitext(filename)
    target = os.path.join(output_dir, filename)
    if not os.path.exists(target):
        return target
    counter = 1
    while True:
        target = os.path.join(output_dir, f"{stem}_{counter}{ext}")
        if not os.path.exists(target):
            return target
        counter += 1


def select_script():
    scripts = get_available_scripts()
    if not scripts:
        print(f"Error: No model generation scripts found in '{SCRIPTS_DIR}'.")
        sys.exit(1)

    # If passed as command-line argument
    if len(sys.argv) > 1:
        arg = sys.argv[1].strip().strip('"').strip("'")
        if arg.isdigit():
            idx = int(arg)
            if 1 <= idx <= len(scripts):
                return scripts[idx - 1]
        for s in scripts:
            if arg.lower() in s.lower():
                return s
        direct_path = os.path.join(SCRIPTS_DIR, arg)
        if os.path.exists(direct_path):
            return arg

    print("===================================================")
    print("             3D Model Script Generator             ")
    print("===================================================\n")
    print("Available 3D Model Scripts:")
    for idx, script_name in enumerate(scripts, 1):
        print(f"  [{idx}] {script_name}")
    print()

    user_input = input("Enter script number or name to run: ").strip().strip('"').strip("'")
    if not user_input:
        print("Defaulting to option [1]")
        return scripts[0]

    if user_input.isdigit():
        idx = int(user_input)
        if 1 <= idx <= len(scripts):
            return scripts[idx - 1]

    # Flexible matching
    clean_in = user_input.lower().replace(" ", "").replace("_", "").replace("-", "")
    for s in scripts:
        clean_s = s.lower().replace(".py", "").replace(" ", "").replace("_", "").replace("-", "")
        if clean_in in clean_s:
            return s

    for s in scripts:
        if user_input.lower() in s.lower():
            return s

    print(f"Error: Could not find script matching '{user_input}'.")
    sys.exit(1)


def main():
    chosen_script = select_script()
    script_path = os.path.join(SCRIPTS_DIR, chosen_script)

    print(f"\nLaunching: {chosen_script}...")
    print("===================================================\n")

    # Snapshot existing files in OUTPUT_DIR before run
    before_output_files = set(os.listdir(OUTPUT_DIR)) if os.path.exists(OUTPUT_DIR) else set()
    before_script_files = set(os.listdir(SCRIPTS_DIR)) if os.path.exists(SCRIPTS_DIR) else set()

    # Execute selected python script
    proc = subprocess.run([sys.executable, script_path], cwd=SCRIPTS_DIR)

    # Check for any new 3D model files created in scripts/ and move them to output/
    if os.path.exists(SCRIPTS_DIR):
        after_script_files = set(os.listdir(SCRIPTS_DIR))
        new_in_scripts = after_script_files - before_script_files
        for item in new_in_scripts:
            if item.lower().endswith((".glb", ".gltf")):
                src = os.path.join(SCRIPTS_DIR, item)
                dest = ensure_unique_destination(OUTPUT_DIR, item)
                shutil.move(src, dest)
                print(f"\n[Moved] Generated model moved to: {dest}")

    # Check newly created models in OUTPUT_DIR
    if os.path.exists(OUTPUT_DIR):
        after_output_files = set(os.listdir(OUTPUT_DIR))
        new_in_output = after_output_files - before_output_files
        if new_in_output:
            print("\n===================================================")
            print("GENERATION COMPLETE! New Output Files:")
            for item in sorted(new_in_output):
                fpath = os.path.join(OUTPUT_DIR, item)
                size_mb = os.path.getsize(fpath) / (1024 * 1024)
                print(f"  -> {item} ({size_mb:.2f} MB)")
            print(f"Directory: {OUTPUT_DIR}")
            print("===================================================\n")

    sys.exit(proc.returncode)


if __name__ == "__main__":
    main()
