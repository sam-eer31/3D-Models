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


def execute_script(script_name):
    """
    Executes a single generator script, moves any generated models from scripts/
    to output/, and returns (success: bool, new_output_files: list).
    """
    script_path = os.path.join(SCRIPTS_DIR, script_name)
    if not os.path.exists(script_path):
        print(f"\n[Error] Script file not found: {script_path}")
        return False, []

    print("\n===================================================")
    print(f"  Launching: {script_name}")
    print("===================================================\n", flush=True)

    # Snapshot existing files in OUTPUT_DIR and SCRIPTS_DIR before run
    before_output_files = set(os.listdir(OUTPUT_DIR)) if os.path.exists(OUTPUT_DIR) else set()
    before_script_files = set(os.listdir(SCRIPTS_DIR)) if os.path.exists(SCRIPTS_DIR) else set()

    # Flush stdout to ensure ordering before child process output
    sys.stdout.flush()

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
                print(f"[Moved] Generated model moved to: {dest}")

    # Detect new files in OUTPUT_DIR
    new_in_output = []
    if os.path.exists(OUTPUT_DIR):
        after_output_files = set(os.listdir(OUTPUT_DIR))
        new_in_output = sorted(list(after_output_files - before_output_files))
        if new_in_output:
            print("\n---------------------------------------------------")
            print(f"GENERATION COMPLETE: Output from {script_name}:")
            for item in new_in_output:
                fpath = os.path.join(OUTPUT_DIR, item)
                if os.path.exists(fpath):
                    size_mb = os.path.getsize(fpath) / (1024 * 1024)
                    print(f"  -> {item} ({size_mb:.2f} MB)")
            print(f"Output Directory: {OUTPUT_DIR}")
            print("---------------------------------------------------")

    if proc.returncode != 0:
        print(f"\n[Warning] {script_name} finished with error code {proc.returncode}.")
        return False, new_in_output

    return True, new_in_output


def generate_all_models(scripts):
    """
    Executes all model scripts in sequence and displays a batch summary.
    """
    print("\n===================================================")
    print(f"       Generating ALL Models ({len(scripts)} total)       ")
    print("===================================================\n")

    succeeded = 0
    failed = 0
    all_new_files = []

    for idx, script_name in enumerate(scripts, 1):
        print(f"\n>>> [{idx}/{len(scripts)}] Running {script_name}...")
        ok, new_files = execute_script(script_name)
        if ok:
            succeeded += 1
        else:
            failed += 1
        all_new_files.extend(new_files)

    print("\n===================================================")
    print("             BATCH GENERATION COMPLETE             ")
    status_msg = f"  Completed: {succeeded}/{len(scripts)} succeeded"
    if failed > 0:
        status_msg += f", {failed} failed"
    print(status_msg)
    if all_new_files:
        print("  Models Created:")
        for item in sorted(set(all_new_files)):
            fpath = os.path.join(OUTPUT_DIR, item)
            if os.path.exists(fpath):
                size_mb = os.path.getsize(fpath) / (1024 * 1024)
                print(f"    -> {item} ({size_mb:.2f} MB)")
        print(f"  Output Directory: {OUTPUT_DIR}")
    print("===================================================\n")


def prompt_menu(scripts):
    """
    Displays the interactive menu and returns:
    ('single', script_name), ('all', None), or ('exit', None)
    """
    all_option_num = len(scripts) + 1

    while True:
        print("===================================================")
        print("             3D Model Script Generator             ")
        print("===================================================\n")
        print("Available 3D Model Options:")
        for idx, script_name in enumerate(scripts, 1):
            print(f"  [{idx}] {script_name}")
        print(f"  [{all_option_num}] Generate ALL models at once (or 'A')")
        print(f"  [Q] Exit")
        print()

        try:
            raw_input = input(f"Enter option (1-{all_option_num}, A for all, Q to exit): ").strip().strip('"').strip("'")
        except (EOFError, KeyboardInterrupt):
            return "exit", None

        user_input = raw_input.lower()

        if user_input in ("q", "quit", "exit", "0"):
            return "exit", None

        if user_input in ("a", "all", "*") or user_input == str(all_option_num):
            return "all", None

        if user_input.isdigit():
            idx = int(user_input)
            if 1 <= idx <= len(scripts):
                return "single", scripts[idx - 1]

        # Flexible name matching for individual scripts
        clean_in = user_input.replace(" ", "").replace("_", "").replace("-", "").replace(".py", "")
        matched = None
        for s in scripts:
            clean_s = s.lower().replace(".py", "").replace(" ", "").replace("_", "").replace("-", "")
            if clean_in and clean_in in clean_s:
                matched = s
                break

        if not matched:
            for s in scripts:
                if user_input and user_input in s.lower():
                    matched = s
                    break

        if matched:
            return "single", matched

        print(f"\n[!] Invalid option '{raw_input}'. Please choose 1-{all_option_num}, 'A' for all, or 'Q' to exit.\n")


def resolve_cli_arg(arg, scripts):
    """
    Resolves a CLI argument into ('single', script_name), ('all', None), or None.
    """
    clean_arg = arg.strip().strip('"').strip("'").lower()
    if clean_arg in ("a", "all", "--all", "-a", "*", str(len(scripts) + 1)):
        return "all", None

    if clean_arg.isdigit():
        idx = int(clean_arg)
        if 1 <= idx <= len(scripts):
            return "single", scripts[idx - 1]

    for s in scripts:
        if clean_arg == s.lower():
            return "single", s

    clean_in = clean_arg.replace(" ", "").replace("_", "").replace("-", "").replace(".py", "")
    for s in scripts:
        clean_s = s.lower().replace(".py", "").replace(" ", "").replace("_", "").replace("-", "")
        if clean_in in clean_s:
            return "single", s

    for s in scripts:
        if clean_arg in s.lower():
            return "single", s

    direct_path = os.path.join(SCRIPTS_DIR, arg)
    if os.path.exists(direct_path):
        return "single", os.path.basename(direct_path)

    return None


def main():
    cli_arg = sys.argv[1] if len(sys.argv) > 1 else None

    while True:
        scripts = get_available_scripts()
        if not scripts:
            print(f"Error: No model generation scripts found in '{SCRIPTS_DIR}'.")
            return

        if cli_arg is not None:
            action_result = resolve_cli_arg(cli_arg, scripts)
            cli_arg = None  # Consume CLI argument on first run only
            if action_result is None:
                print(f"Warning: Could not match argument '{sys.argv[1]}'. Showing menu...\n")
                action, target = prompt_menu(scripts)
            else:
                action, target = action_result
        else:
            action, target = prompt_menu(scripts)

        if action == "exit":
            print("\nExiting 3D Model Builder. Goodbye!")
            break
        elif action == "all":
            generate_all_models(scripts)
        elif action == "single":
            execute_script(target)

        # Ask if the user wants to build another model or exit
        should_continue = False
        while True:
            try:
                choice = input("\nWould you like to build another model? (y/n) [default: n]: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                choice = "n"

            if choice in ("y", "yes"):
                should_continue = True
                print("\n")
                break
            elif choice in ("n", "no", "q", "quit", "exit", ""):
                should_continue = False
                print("\nExiting 3D Model Builder. Goodbye!")
                break
            else:
                print("Please enter 'y' to build more or 'n' to exit.")

        if not should_continue:
            break


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user. Exiting...")
        sys.exit(0)
