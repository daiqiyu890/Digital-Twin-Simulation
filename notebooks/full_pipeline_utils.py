import shutil
from pathlib import Path

def clean_simulation_dirs(project_root, confirm=True, dry_run=False):
    """
    Clean up intermediate and output directories before a new large-scale simulation run.

    Parameters
    ----------
    project_root : Path or str
        Root path of the project (e.g., Path("/Users/qiyudai/Documents/Github/Digital-Twin-Simulation"))
    confirm : bool, optional
        If True, ask for user confirmation before deletion. Default = True.
    dry_run : bool, optional
        If True, only print target directories without deleting or recreating them.
    """
    project_root = Path(project_root)

    # --- define directories to clean ---
    dirs_to_clean = [
        project_root / "text_simulation" / "text_simulation_output" / "csv_persona_level_llm_imputed",
        project_root / "text_simulation" / "text_simulation_output" / "csv_comparison",
        project_root / "text_simulation" / "text_simulation_output" / "csv_persona_level_wave1_3",
        project_root / "t4_simulation" / "text_simulation_output" / "csv_persona_level_wave4"
    ]

    print("=" * 60)
    print("🧹 Cleaning old simulation csv outputs")
    print("=" * 60)

    for d in dirs_to_clean:
        print(f"Target: {d}")

    # --- confirm before delete ---
    if confirm and not dry_run:
        user_input = input("\n⚠️  Confirm deletion of the above directories? (y/n): ").strip().lower()
        if user_input != "y":
            print("❎ Cleaning cancelled.")
            return

    # --- delete & re-create only what was deleted ---
    for d in dirs_to_clean:
        if not d.exists():
            print(f"ℹ️  Directory not found (skipped): {d}")
            continue

        if dry_run:
            print(f"🔍 [Dry Run] Would remove and recreate: {d}")
            continue

        try:
            shutil.rmtree(d)
            print(f"✅ Removed directory: {d}")

            # Recreate the same directory immediately
            d.mkdir(parents=True, exist_ok=True)
            print(f"📁 Recreated clean directory: {d}")

        except Exception as e:
            print(f"⚠️  Failed to remove {d}: {e}")

    print("\n🧩 Cleanup complete. Ready for new simulation run!\n")



def duplicate_folder(src_folder, dst_folder, overwrite=False):
    """
    Duplicate all contents from one folder to another.

    Parameters
    ----------
    src_folder : str or Path
        Source folder path.
    dst_folder : str or Path
        Destination folder path.
    overwrite : bool, optional
        If True, existing files in the destination will be overwritten.
        If False, will raise an error if destination already exists.

    Example
    -------
    duplicate_folder("data/source", "data/backup", overwrite=True)
    """
    src = Path(src_folder)
    dst = Path(dst_folder)

    if not src.exists():
        raise FileNotFoundError(f"❌ Source folder not found: {src}")

    if dst.exists():
        if not overwrite:
            raise FileExistsError(f"⚠️ Destination folder already exists: {dst}")
        else:
            shutil.rmtree(dst)  # delete existing destination before copying

    print(f"📂 Duplicating from: {src}")
    print(f"➡️  To: {dst}")

    shutil.copytree(src, dst)
    print("✅ Duplication completed successfully.")



def detect_error_simulations(output_root: str):
    """
    Scan through each persona folder under text_simulation_output
    and detect simulation runs containing files with 'error' in their names.

    Parameters
    ----------
    output_root : str or Path
        Path to 'text_simulation/text_simulation_output'

    Returns
    -------
    pd.DataFrame
        Summary dataframe with columns:
        ['persona_id', 'sim_folder', 'error_files']
    """
    output_root = Path(output_root)
    results = []

    if not output_root.exists():
        raise FileNotFoundError(f"❌ Output folder not found: {output_root}")

    print(f"🔍 Scanning simulation outputs in: {output_root}\n")

    # iterate through persona directories
    for pid_dir in sorted(output_root.glob("pid_*")):
        if not pid_dir.is_dir():
            continue
        
        persona_id = pid_dir.name
        sim_dirs = [d for d in pid_dir.iterdir() if d.is_dir() and "sim" in d.name]

        for sim_dir in sim_dirs:
            error_files = [f.name for f in sim_dir.glob("*") if "error" in f.name.lower()]
            if error_files:
                results.append({
                    "persona_id": persona_id,
                    "sim_folder": sim_dir.name,
                    "error_files": ", ".join(error_files)
                })
    
    # Create DataFrame summary
    df_errors = pd.DataFrame(results)
    if not df_errors.empty:
        print(f"⚠️ Found {len(df_errors)} simulations containing errors.\n")
        print(df_errors.head())
    else:
        print("✅ No error files detected across all personas.")

    return df_errors


def clean_error_simulations_no_confirm(output_root: str):
    """
    Detect and delete simulation folders containing 'error' files.
    Additionally, detect missing simulation numbers (e.g., if 1,2,5 exist → detect 3,4 missing).
    Does NOT rename folders.

    Parameters
    ----------
    output_root : str or Path
        Path to 'text_simulation/text_simulation_output'

    Returns
    -------
    dict
        {
            "deleted_df": pd.DataFrame([...]),
            "missing_sims": dict(pid_xxx -> [missing_indices])
        }
    """
    output_root = Path(output_root)
    deleted_records = []
    missing_sims_dict = {}

    if not output_root.exists():
        raise FileNotFoundError(f"❌ Output folder not found: {output_root}")

    print(f"🔍 Scanning for error-containing or missing simulations in: {output_root}\n")

    for pid_dir in sorted(output_root.glob("pid_*")):
        if not pid_dir.is_dir():
            continue

        persona_id = pid_dir.name
        sim_dirs = [d for d in pid_dir.iterdir() if d.is_dir() and "sim" in d.name]

        # --- Step 1: detect & delete error-containing simulations ---
        for sim_dir in sim_dirs:
            error_files = [f.name for f in sim_dir.glob("*") if "error" in f.name.lower()]
            if error_files:
                record = {
                    "persona_id": persona_id,
                    "sim_folder": sim_dir.name,
                    "deleted_path": str(sim_dir),
                    "error_files": ", ".join(error_files)
                }
                deleted_records.append(record)
                try:
                    shutil.rmtree(sim_dir)
                    print(f"🗑️ Deleted {sim_dir.name} (found: {record['error_files']})")
                except Exception as e:
                    print(f"❌ Failed to delete {sim_dir}: {e}")


    # --- Step 4: summary ---
    df_deleted = pd.DataFrame(deleted_records)
    if not df_deleted.empty:
        print(f"\n✅ Deleted {len(df_deleted)} simulation folders containing errors.")
    else:
        print("✅ No error-containing simulations found.")


    return {
        "deleted_df": df_deleted
    }