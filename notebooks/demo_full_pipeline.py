#Step1: Setup and Configuration

# Import required libraries
import os
import sys
import json
import yaml
from pathlib import Path
from dotenv import load_dotenv
import time

#set up the open AI key
import os
os.environ["OPENAI_API_KEY"] = "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"

# Direct path setup - adjust this path if your project is in a different location
PROJECT_ROOT_PATH = "/Users/qiyudai/Documents/Github/Digital-Twin-Simulation"

# Set up project root
project_root = Path(PROJECT_ROOT_PATH)

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

#clean existing results
clean_simulation_dirs(project_root, confirm=True)

# Configuration
MAX_PERSONAS = 1  # Limit for demo purposes

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
load_dotenv(project_root / '.env')

# Check OpenAI API key
if not os.getenv("OPENAI_API_KEY"):
    print("⚠️  Please set your OPENAI_API_KEY in the .env file")
else:
    print("✅ OpenAI API key loaded successfully")

print(f"\nConfigured to process {MAX_PERSONAS} personas for this demo")


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
print("Step 4: Convert Questions to Text")
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
print("Step 5: Create Simulation Input")
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


#Step 7: Run LLM simulations
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

print("=" * 60)
print("Step 6: Run LLM Simulations")
print("=" * 60)

print("\nRunning LLM simulations...")
print("This may take a few minutes depending on the number of personas and API rate limits.\n")

# Use subprocess to run the simulation with proper Python path
import subprocess

# Set up environment with proper PYTHONPATH
env = os.environ.copy()
env['PYTHONPATH'] = str(project_root) + os.pathsep + str(project_root / 'text_simulation') + os.pathsep + env.get('PYTHONPATH', '')

# Run the simulation script
process = subprocess.Popen(
    [
        sys.executable, 
        str(project_root / "text_simulation" / "run_LLM_simulations.py"),
        "--config", str(project_root / "text_simulation" / "configs" / "openai_config.yaml"),
        "--max_personas", str(MAX_PERSONAS)
    ],
    cwd=str(project_root),
    env=env,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True
)

# Stream output
try:
    for line in process.stdout:
        print(line.rstrip())
    
    process.wait()
    
    if process.returncode == 0:
        print("\n✅ Simulations completed successfully")
    else:
        print(f"\n❌ Error running simulations (exit code: {process.returncode})")
except KeyboardInterrupt:
    print("\n⚠️  Simulation interrupted by user")
    process.terminate()
    process.wait()