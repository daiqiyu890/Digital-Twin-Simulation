import shutil

def clean_simulation_dirs(project_root, confirm=True):
    """
    Clean up intermediate and output directories before a new large-scale simulation run.

    Parameters
    ----------
    project_root : Path
        Root path of the project (e.g., Path("/Users/qiyudai/Documents/Github/Digital-Twin-Simulation"))
    confirm : bool, optional
        If True, ask for user confirmation before deletion. Set to False for fully automated pipelines.
    """
    # Define directories to clean
    dirs_to_clean = [
        project_root / "text_simulation" / "text_personas",
        project_root / "text_simulation" / "text_simulation_input",
        project_root / "text_simulation" / "text_simulation_output"

    ]
    
    print("=" * 60)
    print("🧹 Cleaning old simulation outputs")
    print("=" * 60)

    # Print summary
    for d in dirs_to_clean:
        print(f"Target: {d}")

    if confirm:
        user_input = input("\n⚠️  Confirm deletion of the above directories? (y/n): ").strip().lower()
        if user_input != "y":
            print("❎ Cleaning cancelled.")
            return

    # Perform cleaning
    for d in dirs_to_clean:
        if d.exists():
            try:
                shutil.rmtree(d)
                print(f"✅ Removed directory: {d}")
            except Exception as e:
                print(f"⚠️  Failed to remove {d}: {e}")
        else:
            print(f"ℹ️  Directory not found (skipped): {d}")
    
    # Recreate main folders for next run
    for d in [project_root / "text_simulation" / "text_personas",
              project_root / "text_simulation" / "text_simulation_output"]:
        d.mkdir(parents=True, exist_ok=True)
        print(f"📁 Recreated clean directory: {d}")
    
    print("\n🧩 Cleanup complete. Ready for new simulation run!\n")
