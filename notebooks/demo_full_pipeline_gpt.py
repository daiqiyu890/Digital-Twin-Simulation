# cd /Users/qiyudai/Documents/Github/Digital-Twin-Simulation
# cd /scratch/qd2177/research/Digital-Twin-Simulation

#Step1: Setup and Configuration
# Import required libraries
import os
import sys
import json
import yaml
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
import time
from text_simulation.full_pipeline_utils import *

# API keys are loaded from ENV_PATH below; do not commit real keys into code.

# Direct path setup - works on both local Mac and Torch/HPC.
PROJECT_ROOT_CANDIDATES = [
    Path("/Users/qiyudai/Documents/Github/Digital-Twin-Simulation"),
    Path("/scratch/qd2177/research/Digital-Twin-Simulation"),
]
project_root = next((p for p in PROJECT_ROOT_CANDIDATES if p.exists()), None)
if project_root is None:
    raise RuntimeError(
        "Project root not found. Checked: "
        + ", ".join(str(p) for p in PROJECT_ROOT_CANDIDATES)
    )
PROJECT_ROOT_PATH = str(project_root)

# Verify the project root exists and has expected directories
if not project_root.exists():
    raise RuntimeError(f"Project root not found at: {project_root}")

if not (project_root / 'text_simulation').exists():
    raise RuntimeError(f"'text_simulation' directory not found in: {project_root}")

if not (project_root / 'evaluation').exists():
    raise RuntimeError(f"'evaluation' directory not found in: {project_root}")

# Add project root to Python path
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Configuration
# Use MAX_PERSONAS as the single source of truth for this demo script.
# When this script runs, it writes this value into openai_config.yaml and
# also reuses it for evaluation/json2csv below.
# =========================
# User-specified parameters
# Change these when running a new experiment.
# =========================

# Experiment size
MAX_PERSONAS = 100
NUM_SIMULATIONS_PER_PERSONA = 50

# Provider/model choice
# PROVIDER must be one of:
#   openai
#   deepseek
#   claude      # alias: anthropic
#   anthropic   # same backend as claude
#   gemini
#
# MODEL_NAME should be a model id supported by the selected provider.
# Common examples:
#   openai:   gpt-4.1-mini-2025-04-14, gpt-4.1, gpt-4o-mini, gpt-4o
#   deepseek: deepseek-v4-flash, deepseek-v4-pro
#   claude:   claude-3-5-sonnet-20241022, claude-3-5-haiku-20241022
#   gemini:   gemini-2.5-flash, gemini-3-pro
#
# API keys are loaded from:
#   /Users/qiyudai/Documents/Github/Digital-Twin-Simulation/.env
#   OPENAI_API_KEY=...
#   DEEPSEEK_API_KEY=...
#   ANTHROPIC_API_KEY=...
#   GOOGLE_API_KEY=...
ENV_PATH = project_root / ".env"
if not ENV_PATH.exists():
    ENV_PATH = project_root / "notebooks" / ".env"
PROVIDER = "openai"
MODEL_NAME = "gpt-4.1-mini-2026-08-10"

# Common generation parameters
TEMPERATURE = 1
MAX_TOKENS = 16384

# Runtime/retry parameters
NUM_WORKERS = 12
MAX_RETRIES = 8

# Provider-specific API parameters.
# Fill only the provider you are using; leave others as {}.
# Examples:
#   DeepSeek: {"base_url": "https://api.deepseek.com"}
#   Claude: {"thinking": {"type": "enabled", "budget_tokens": 1024}}
#   Gemini: {"thinking_config": {"thinking_budget": 1024}}
PROVIDER_MODEL_PARAMS = {
    "openai": {},
    "deepseek": {"base_url": "https://api.deepseek.com", "extra_body": {"thinking": {"type": "disabled"}}},
    "claude": {},
    "anthropic": {},
    "gemini": {},
}

# =========================
# Derived paths
# Normally do not edit these directly.
# =========================

MODEL_DIR_NAME = MODEL_NAME.replace("/", "-")
RUN_NAME = f"temp_{TEMPERATURE}"
OUTPUT_FOLDER_DIR = f"text_simulation_output/{PROVIDER}/{MODEL_DIR_NAME}/{RUN_NAME}"

RUN_OUTPUT_ROOT = project_root / "text_simulation" / OUTPUT_FOLDER_DIR
RUN_OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

#clean existing csv files
clean_simulation_dirs(project_root, output_root=RUN_OUTPUT_ROOT, confirm=True)

#clean existing files with error
missing_info = clean_error_simulations_no_confirm(
    output_root=RUN_OUTPUT_ROOT
)

#duplicate current results to dropbox
src_folder = RUN_OUTPUT_ROOT
dst_folder="/scratch/qd2177/research/back-up files"
# duplicate_folder(src_folder, dst_folder, overwrite=True)

print(f"✅ Project root: {project_root}")
print(f"Current directory: {Path.cwd()}")
print(f"Python path configured: {sys.path[0]}")

# Set notebook directory
notebook_dir = project_root / 'notebooks'

# Setup environment
print("=" * 60)
print("Digital Twin Simulation - Full Pipeline Demo")
print("=" * 60)
print()

# Load environment variables
load_dotenv(ENV_PATH)

# Check the API key
config_path = project_root / "text_simulation" / "configs" / "openai_config.yaml"
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)
provider = PROVIDER

if provider == "openai":
    api_key = os.getenv("OPENAI_API_KEY")
elif provider == "deepseek":
    api_key = os.getenv("DEEPSEEK_API_KEY")
elif provider in {"claude", "anthropic"}:
    api_key = os.getenv("ANTHROPIC_API_KEY")
elif provider == "gemini":
    api_key = os.getenv("GOOGLE_API_KEY")
else:
    api_key = None

if not api_key:
    print(f"⚠️  Please set your {provider.upper()}_API_KEY in {ENV_PATH}")
else:
    print(f"✅ {provider.upper()} API key loaded successfully")


#Step 2: load the dataset
print("=" * 60)
print("Step 1: Download Dataset")
print("=" * 60)

data_dir = project_root / "data"
if (data_dir / "mega_persona_json" / "mega_persona").exists():
    print("✅ Dataset already downloaded")
else:
    print("Downloading dataset...")
    # Save current directory
    original_cwd = Path.cwd()
    
    try:
        # Change to project root for download
        os.chdir(project_root)
        
        # Import and run the download function directly
        import download_dataset
        download_dataset.main()
        print("✅ Dataset downloaded successfully")
    except Exception as e:
        print(f"❌ Error downloading dataset: {e}")
    finally:
        # Restore original directory
        os.chdir(original_cwd)

#Step 3: Update Configuration
print("=" * 60)
print("Step 2: Update Configuration")
print("=" * 60)

config_path = project_root / "text_simulation" / "configs" / "openai_config.yaml"

try:
    # Read current config
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Update max_personas
    config['max_personas'] = MAX_PERSONAS
    config['num_simulations_per_persona']=NUM_SIMULATIONS_PER_PERSONA
    config['num_workers'] = NUM_WORKERS
    config['max_retries'] = MAX_RETRIES
    config['temperature'] = TEMPERATURE
    config['max_tokens'] = MAX_TOKENS
    config['provider'] = PROVIDER
    config['model_name'] = MODEL_NAME
    config['run_name'] = RUN_NAME
    config['output_folder_dir'] = OUTPUT_FOLDER_DIR
    config['provider_model_params'] = PROVIDER_MODEL_PARAMS
    
    # Write back
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)
    
    print(f"✅ Updated config to process {MAX_PERSONAS} personas")
except Exception as e:
    print(f"❌ Error updating config: {e}")


#Step 4: Convert Personas to text format
print("=" * 60)
print("Step 3: Convert Personas to Text")
print("=" * 60)

# Import the conversion function
from text_simulation.convert_persona_to_text import convert_persona_to_text
from tqdm import tqdm

# Set up paths
persona_json_dir = project_root / "data" / "mega_persona_json" / "mega_persona"
output_text_dir = project_root / "text_simulation" / "text_personas"

# Create output directory
output_text_dir.mkdir(parents=True, exist_ok=True)

try:
    # Get persona files and limit to MAX_PERSONAS for demo
    json_files = [f for f in os.listdir(persona_json_dir) 
                  if f.endswith('.json') and f.startswith('pid_')]
    
    # Limit files for demo
    files_to_process = json_files[:MAX_PERSONAS]
    
    print(f"Converting {len(files_to_process)} personas (limited for demo)...")
    
    successful = 0
    failed = 0
    skipped=0
    
    for json_file in tqdm(files_to_process, desc="Converting personas"):
        input_path = persona_json_dir / json_file
        output_path = output_text_dir / json_file.replace('.json', '.txt')
    

        if convert_persona_to_text(str(input_path), str(output_path), "full"):
            successful += 1
        else:
            failed += 1
            print(f"Failed to convert {json_file}")
    
    print(f"\n✅ Conversion complete. Successful: {successful}, Failed: {failed}")
    
    # Check output directory
    persona_files = list(output_text_dir.glob("*.txt"))
    print(f"   Created {len(persona_files)} persona text files")
    
except Exception as e:
    print(f"❌ Error converting personas: {e}")


#Step 5: Convert Questions to text format
print("=" * 60)
print("Step 5: Convert Questions to Text")
print("=" * 60)

# Use subprocess to run the script with proper Python path
import subprocess

# Run the script with PYTHONPATH set to include text_simulation directory
env = os.environ.copy()
env['PYTHONPATH'] = str(project_root / 'text_simulation') + os.pathsep + env.get('PYTHONPATH', '')

result = subprocess.run(
    [sys.executable, str(project_root / "text_simulation" / "convert_question_json_to_text.py")],
    cwd=str(project_root),
    env=env,
    capture_output=True,
    text=True
)

if result.returncode == 0:
    print("✅ Questions converted successfully")
    
    # Check output
    output_dir = project_root / "text_simulation" / "text_questions"
    if output_dir.exists():
        question_files = list(output_dir.glob("*.txt"))
        print(f"   Created {len(question_files)} question text files")
else:
    print(f"❌ Error converting questions: {result.stderr}")
    # If it still fails, suggest manual fix
    print("\nNote: If this continues to fail, you can run manually:")
    print(f"  cd {project_root}")
    print("  python text_simulation/convert_question_json_to_text.py")

#Step 6: Create Simulation Input
print("=" * 60)
print("Step 6: Create Simulation Input")
print("=" * 60)

# Import the function
from text_simulation.create_text_simulation_input import create_combined_prompts

# Set up paths
persona_text_dir = str(project_root / "text_simulation" / "text_personas")
question_prompts_dir = str(project_root / "text_simulation" / "text_questions")
output_combined_prompts_dir = str(project_root / "text_simulation" / "text_simulation_input")

try:
    create_combined_prompts(
        persona_text_dir=persona_text_dir,
        question_prompts_dir=question_prompts_dir,
        output_combined_prompts_dir=output_combined_prompts_dir
    )
    
    print("✅ Simulation input created successfully")
    
    # Check how many input files were created
    input_dir = Path(output_combined_prompts_dir)
    if input_dir.exists():
        prompt_files = list(input_dir.glob("*_prompt.txt"))
        print(f"   Created {len(prompt_files)} prompt files")
        
        # Limit to MAX_PERSONAS for demo
        if len(prompt_files) > MAX_PERSONAS:
            print(f"   (Will process only first {MAX_PERSONAS} for this demo)")
    
except Exception as e:
    print(f"❌ Error creating simulation input: {e}")


# Step 7: Pre-check — Identify complete / incomplete personas
print("=" * 60)
print("Step 7: Pre-check: Determine complete and incomplete personas")
print("=" * 60)

output_sim_dir = RUN_OUTPUT_ROOT


# Count how many simulations exist for each persona
pid_sim_counts = {}
if output_sim_dir.exists():
    for pid_dir in output_sim_dir.iterdir():
        if pid_dir.is_dir() and pid_dir.name.startswith("pid_"):
            sim_dirs = [d for d in pid_dir.iterdir() if d.is_dir() and "sim" in d.name]
            pid_sim_counts[pid_dir.name] = len(sim_dirs)

complete_pids = []
incomplete_pids = []
new_pids = []

# All persona JSON files (the source list)
json_files = [
    f for f in os.listdir(project_root / "data" / "mega_persona_json" / "mega_persona")
    if f.endswith(".json") and f.startswith("pid_")
][:MAX_PERSONAS]

for f in json_files:
    pid = f.replace(".json", "")
    count = pid_sim_counts.get(pid, 0)

    if count == 0:
        print(f"🆕 {pid}: no simulations yet → will run {NUM_SIMULATIONS_PER_PERSONA}")
        new_pids.append(pid)
    elif count < NUM_SIMULATIONS_PER_PERSONA:
        remaining = NUM_SIMULATIONS_PER_PERSONA - count
        print(f"⚠️ {pid}: {count}/{NUM_SIMULATIONS_PER_PERSONA} done → will run {remaining} more")
        incomplete_pids.append(pid)
    else:
        print(f"✅ {pid}: {count}/{NUM_SIMULATIONS_PER_PERSONA} complete → skip")
        complete_pids.append(pid)

# Personas that still need runs
pids_to_run = new_pids + incomplete_pids
pids_to_run = [pid.replace("_mega_persona", "") for pid in pids_to_run]
if not pids_to_run:
    print("\n🎉 All personas complete — skipping simulation stage.\n")
    skip_simulations = True
else:
    skip_simulations = False
    print(f"\n🚀 Need to run simulations for {len(pids_to_run)} personas:")
    print(", ".join(pids_to_run))


# ============================================
# Step 8: Run LLM Simulations (Sequential Mode)
# ============================================

import subprocess
import time
import datetime

# Display current configuration
config_path = project_root / "text_simulation" / "configs" / "openai_config.yaml"
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

print("Current simulation configuration:")
print(f"  Model: {config['model_name']}")
print(f"  Temperature: {config['temperature']}")
print(f"  Max personas: {config['max_personas']}")
print(f"  Workers: {config['num_workers']}")
print(f"  Force regenerate: {config['force_regenerate']}")
print(f"  Number of Simulations Per Persona: {config['num_simulations_per_persona']}")
print("=" * 60)
print("Step 8: Run LLM Simulations (Sequential Mode)")
print("=" * 60)
print("\nThis will run each persona one-by-one to prevent rate-limit or batch failures.\n")

if skip_simulations:
    print("✅ All personas already finished. Skipping simulation step.")
else:
    env = os.environ.copy()
    env["PYTHONPATH"] = (
        str(project_root)
        + os.pathsep
        + str(project_root / "text_simulation")
        + os.pathsep
        + env.get("PYTHONPATH", "")
    )

    # ✅ Create log file
    log_path = project_root / f"simulation_run_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    log_file = open(log_path, "w", encoding="utf-8")

    print("=" * 60)
    print(f"🧠 Starting sequential simulation run at {datetime.datetime.now()}")
    print(f"📝 Logging to: {log_path}")
    print("=" * 60)

    failed_pids = []

    for pid in pids_to_run:
        print(f"\n🚀 Running simulation for persona: {pid}")
        print("-" * 60)
        log_file.write(f"\n[{datetime.datetime.now()}] Running simulation for {pid}\n")

        process = subprocess.Popen(
            [
                sys.executable,
                str(project_root / "text_simulation" / "run_LLM_simulations.py"),
                "--config",
                str(project_root / "text_simulation" / "configs" / "openai_config.yaml"),
                "--max_personas",
                "1",  # 每次只跑一个人
                "--num_simulations_per_persona",
                str(NUM_SIMULATIONS_PER_PERSONA),
                "--pids",
                pid,
            ],
            cwd=str(project_root),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        for line in process.stdout:
            print(line.rstrip())
            log_file.write(line)

        process.wait()

        if process.returncode == 0:
            print(f"✅ {pid} completed successfully.")
            log_file.write(f"[{datetime.datetime.now()}] ✅ {pid} completed successfully.\n")
        else:
            print(f"❌ {pid} failed (exit code: {process.returncode})")
            log_file.write(f"[{datetime.datetime.now()}] ❌ {pid} failed.\n")
            failed_pids.append(pid)

        # ✅ 每次之间暂停 5 秒，避免 API 限速
        print("⏸️  Waiting 5 seconds before next persona...\n")
        time.sleep(5)

    log_file.close()

    print("\n🎯 All sequential simulations finished.")
    print(f"📘 Full log saved at: {log_path}")

    if failed_pids:
        print(f"\n⚠️ The following personas failed: {', '.join(failed_pids)}")
        fail_path = project_root / "failed_personas.txt"
        with open(fail_path, "w") as f:
            f.write("\n".join(failed_pids))
        print(f"📝 Saved failed persona IDs to: {fail_path}")
    else:
        print("✅ All personas completed successfully.")


#Step 9: Examine Simulation Results
print("=" * 60)
print("Step 9: Examine Results")
print("=" * 60)

output_dir = RUN_OUTPUT_ROOT

if output_dir.exists():
    persona_dirs = [d for d in output_dir.iterdir() if d.is_dir() and d.name.startswith("pid_")]
    print(f"Found {len(persona_dirs)} persona output directories\n")
    
    # Show a sample response
    if persona_dirs:
        sample_dir = persona_dirs[0]
        response_files = list(sample_dir.glob("**/*_response.json"))
        
        if response_files:
            with open(response_files[0], 'r') as f:
                response = json.load(f)
            
            print(f"Sample response from {sample_dir.name}:")
            print("=" * 50)
            print(f"Prompt ID: {response.get('question_id', 'N/A')}")
            print(f"\nPrompt (first 200 chars):")
            print(response.get('prompt_text', '')[:200] + "...")
            print(f"\nResponse (first 500 chars):")
            response_text = response.get('response_text', 'No response')
            if len(response_text) > 500:
                print(response_text[:500] + "...")
            else:
                print(response_text)
            print("=" * 50)
else:
    print("No output directory found")


#Step 10: Convert JSON to CSV for Evaluation
print("=" * 60)
print("Step 10: Convert JSON to CSV for Evaluation")
print("=" * 60)

# Create evaluation config for json2csv
eval_config = {
    "trial_dir": f"text_simulation/{OUTPUT_FOLDER_DIR}/",
    "model_name": MODEL_NAME,
    "max_personas": MAX_PERSONAS,
    "waves": {
        "wave1_3": {
            "input_pattern": "data/mega_persona_json/answer_blocks/pid_{pid}_wave4_Q_wave1_3_A.json",
            "output_csv": "${trial_dir}/csv_comparison/responses_wave1_3.csv",
            "output_csv_formatted": "${trial_dir}/csv_comparison/csv_formatted/responses_wave1_3_formatted.csv",
            "output_csv_labeled": "${trial_dir}/csv_comparison/csv_formatted_label/responses_wave1_3_label_formatted.csv"
        },
        "wave4": {
            "input_pattern": "data/mega_persona_json/answer_blocks/pid_{pid}_wave4_Q_wave4_A.json",
            "output_csv": "${trial_dir}/csv_comparison/responses_wave4.csv",
            "output_csv_formatted": "${trial_dir}/csv_comparison/csv_formatted/responses_wave4_formatted.csv",
            "output_csv_labeled": "${trial_dir}/csv_comparison/csv_formatted_label/responses_wave4_label_formatted.csv"
        },
        "llm_imputed": {
            "input_pattern": "${trial_dir}/answer_blocks_llm_imputed/pid_{pid}/**/pid_{pid}_*wave4_Q_wave4_A.json",
            "output_csv": "${trial_dir}/csv_comparison/responses_llm_imputed.csv",
            "output_csv_formatted": "${trial_dir}/csv_comparison/csv_formatted/responses_llm_imputed_formatted.csv",
            "output_csv_labeled": "${trial_dir}/csv_comparison/csv_formatted_label/responses_llm_imputed_label_formatted.csv"
        }
    },
    "benchmark_csv": "data/wave_csv/wave_4_numbers_anonymized.csv",
    "column_mapping": "evaluation/column_mapping.csv",
    "save_question_mapping": True,
    "question_mapping_output": "${trial_dir}/csv_comparison/question_mapping.csv",
    "generate_randdollar_breakdown": True,
    "randdollar_output": "${trial_dir}/csv_comparison/randdollar_breakdown.csv"
}

# Write temporary config file
temp_eval_config = project_root / "temp_eval_config.yaml"
with open(temp_eval_config, 'w') as f:
    yaml.dump(eval_config, f)

print("Converting JSON results to CSV format...")

# Run json2csv conversion
result = subprocess.run(
    [sys.executable, "evaluation/json2csv.py", "--config", str(temp_eval_config), "--all", "--verbose"],
    cwd=str(project_root),
    capture_output=True,
    text=True
)

if result.returncode == 0:
    print("✅ JSON to CSV conversion completed successfully")
    
    # Check what was created
    csv_dir = RUN_OUTPUT_ROOT / "csv_comparison"
    if csv_dir.exists():
        csv_files = list((csv_dir / "csv_formatted").glob("*.csv")) if (csv_dir / "csv_formatted").exists() else []
        print(f"   Generated {len(csv_files)} formatted CSV files")
        if csv_files:
            print("   Files created:")
            for f in csv_files[:5]:  # Show first 5 files
                print(f"     - {f.name}")
else:
    print(f"⚠️  JSON to CSV conversion encountered issues")
    print(f"   Error: {result.stderr[:500]}...")  # Show first 500 chars of error
    
# Clean up temp config
if temp_eval_config.exists():
    temp_eval_config.unlink()

print(f"\nOutput directory: {csv_dir}")


#Step 10: check if the combined ground truth file is correct
import pandas as pd
from pathlib import Path

#folder=Path("/home/users/s1155141616/Digital-Twin-Simulation/text_simulation/text_simulation_output/csv_persona_level_wave1_3")
folder = RUN_OUTPUT_ROOT / "csv_persona_level_wave1_3"
csv_files = sorted(folder.glob("pid_*.csv"))

# 读取并合并
df_list = []
for file in csv_files:
    try:
        df = pd.read_csv(file)
        df_list.append(df)
    except Exception as e:
        print(f"⚠️ Failed to read {file.name}: {e}")

combined_df = pd.concat(df_list, ignore_index=True)
first_col = combined_df.columns[0]
combined_df = combined_df.sort_values(by=first_col).reset_index(drop=True)

# 输出结果
output_path = folder / "combined_persona_wave1_3.csv"
combined_df.to_csv(output_path, index=False, encoding="utf-8-sig")

print(f"✅ Combined CSV saved to: {output_path}")
