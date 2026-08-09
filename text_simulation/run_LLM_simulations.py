import argparse
import asyncio
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import yaml
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from text_simulation.llm_helper import LLMConfig, process_prompts_batch
from text_simulation.postprocess_responses import postprocess_simulation_outputs_with_pid


def safe_name(value: str) -> str:
    value = str(value).strip().replace("/", "-")
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_")


def resolve_project_root() -> Path:
    return PROJECT_ROOT


def resolve_text_simulation_path(project_root: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    if path.parts and path.parts[0] == "text_simulation":
        return project_root / path
    return project_root / "text_simulation" / path


def load_config(config_path: Path) -> Dict:
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}
    provider = config.get("provider") or config.get("model_provider") or "openai"
    config["provider"] = provider
    return config


def build_output_folder_name(config: Dict) -> str:
    provider = safe_name(config.get("provider", "openai"))
    model = safe_name(config.get("model_name", "model"))
    run_name = config.get("run_name")
    if run_name:
        return safe_name(run_name)
    return f"{provider}_{model}"


def get_output_root(project_root: Path, config: Dict) -> Path:
    output_folder = config.get("output_folder_dir")
    if not output_folder:
        output_folder = f"text_simulation_output/{build_output_folder_name(config)}"
    return resolve_text_simulation_path(project_root, output_folder)


def get_provider_params(config: Dict) -> Dict:
    provider = config.get("provider", "openai")
    provider_params = config.get("provider_params", {}) or {}
    by_provider = config.get("provider_model_params", {}) or {}
    selected_provider_params = by_provider.get(provider, {}) or {}
    return {**selected_provider_params, **provider_params}


def select_prompt_files(input_root: Path, max_personas: Optional[int], pids: Optional[List[str]]) -> List[Path]:
    prompt_files = sorted(input_root.glob("pid_*_prompt.txt"), key=lambda p: p.name)
    if pids:
        wanted = {pid if pid.startswith("pid_") else f"pid_{pid}" for pid in pids}
        prompt_files = [
            p for p in prompt_files
            if p.name.replace("_prompt.txt", "") in wanted
        ]
    if max_personas is not None:
        prompt_files = prompt_files[:max_personas]
    return prompt_files


def existing_successful_sim_dirs(output_root: Path, pid: str) -> set:
    pid_dir = output_root / pid
    if not pid_dir.exists():
        return set()
    out = set()
    for sim_dir in pid_dir.iterdir():
        if not sim_dir.is_dir() or "_sim" not in sim_dir.name:
            continue
        response_path = sim_dir / f"{sim_dir.name}_response.json"
        if response_path.exists():
            out.add(sim_dir.name)
    return out


def build_prompt_jobs(
    prompt_files: Iterable[Path],
    output_root: Path,
    num_simulations_per_persona: int,
    force_regenerate: bool,
) -> List[Tuple[str, str]]:
    jobs = []
    for prompt_file in prompt_files:
        pid = prompt_file.name.replace("_prompt.txt", "")
        prompt_text = prompt_file.read_text(encoding="utf-8")
        existing = existing_successful_sim_dirs(output_root, pid)
        for sim_idx in range(1, num_simulations_per_persona + 1):
            prompt_id = f"{pid}_sim{sim_idx:03d}"
            if not force_regenerate and prompt_id in existing:
                continue
            jobs.append((prompt_id, prompt_text))
    return jobs


def save_and_verify_response(
    prompt_id: str,
    llm_response_data: Dict,
    original_prompt_text: str,
    *,
    output_root: str,
    question_json_base_dir: str,
):
    output_root_path = Path(output_root)
    base_pid = prompt_id.split("_sim")[0]
    sim_dir = output_root_path / base_pid / prompt_id
    sim_dir.mkdir(parents=True, exist_ok=True)
    response_path = sim_dir / f"{prompt_id}_response.json"

    payload = {
        "persona_id": base_pid,
        "question_id": prompt_id,
        "prompt_text": original_prompt_text,
        "response_text": llm_response_data.get("response_text", ""),
        "usage_details": llm_response_data.get("usage_details", {}),
        "provider": llm_response_data.get("provider"),
        "reasoning_content": llm_response_data.get("reasoning_content"),
        "llm_call_error": llm_response_data.get("error"),
    }
    with open(response_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    if payload["llm_call_error"]:
        return False

    return postprocess_simulation_outputs_with_pid(
        prompt_id,
        str(output_root_path),
        question_json_base_dir,
        str(output_root_path / "answer_blocks_llm_imputed"),
    )


async def run_simulations(args):
    project_root = resolve_project_root()
    load_dotenv(project_root / ".env")

    config_path = Path(args.config) if args.config else project_root / "text_simulation" / "configs" / "openai_config.yaml"
    if not config_path.is_absolute():
        config_path = project_root / config_path
    config = load_config(config_path)

    if args.max_personas is not None:
        config["max_personas"] = args.max_personas
    if args.num_simulations_per_persona is not None:
        config["num_simulations_per_persona"] = args.num_simulations_per_persona
    if args.provider:
        config["provider"] = args.provider
    if args.model_name:
        config["model_name"] = args.model_name
    if args.output_folder_dir:
        config["output_folder_dir"] = args.output_folder_dir

    input_root = resolve_text_simulation_path(project_root, config.get("input_folder_dir", "text_simulation_input"))
    output_root = get_output_root(project_root, config)
    output_root.mkdir(parents=True, exist_ok=True)

    pids = [p.strip() for p in args.pids.split(",") if p.strip()] if args.pids else None
    prompt_files = select_prompt_files(input_root, config.get("max_personas"), pids)
    if not prompt_files:
        raise RuntimeError(f"No prompt files found in {input_root}")

    jobs = build_prompt_jobs(
        prompt_files,
        output_root,
        int(config.get("num_simulations_per_persona", 1)),
        bool(config.get("force_regenerate", False)),
    )

    print("Simulation configuration:")
    print(f"  Provider: {config.get('provider')}")
    print(f"  Model: {config.get('model_name')}")
    print(f"  Personas selected: {len(prompt_files)}")
    print(f"  Jobs to run: {len(jobs)}")
    print(f"  Output root: {output_root}")

    if not jobs:
        print("All selected simulations already exist. Nothing to run.")
        return

    llm_config = LLMConfig(
        model_name=config["model_name"],
        temperature=config.get("temperature"),
        max_tokens=config.get("max_tokens"),
        system_instruction=config.get("system_instruction"),
        max_retries=int(config.get("max_retries", 10)),
        max_concurrent_requests=int(config.get("num_workers", 5)),
        provider_params=get_provider_params(config),
        verification_callback=save_and_verify_response,
        verification_callback_args={
            "output_root": str(output_root),
            "question_json_base_dir": str(project_root / "data" / "mega_persona_json" / "answer_blocks"),
        },
    )

    results = await process_prompts_batch(
        jobs,
        llm_config,
        provider=config["provider"],
        desc=f"{config['provider']} simulations",
    )
    errors = {pid: data for pid, data in results.items() if data.get("error")}
    print(f"Finished {len(results)} jobs; errors: {len(errors)}")
    if errors:
        error_path = output_root / "simulation_errors.json"
        with open(error_path, "w", encoding="utf-8") as f:
            json.dump(errors, f, ensure_ascii=False, indent=2)
        print(f"Saved errors to: {error_path}")


def parse_args():
    parser = argparse.ArgumentParser(description="Run Digital Twin LLM simulations.")
    parser.add_argument("--config", default=None, help="Path to YAML config.")
    parser.add_argument("--max_personas", type=int, default=None)
    parser.add_argument("--num_simulations_per_persona", type=int, default=None)
    parser.add_argument("--pids", default=None, help="Comma-separated pids, e.g. pid_1,pid_2")
    parser.add_argument("--provider", default=None, choices=["openai", "deepseek", "claude", "anthropic", "gemini"])
    parser.add_argument("--model_name", default=None)
    parser.add_argument("--output_folder_dir", default=None)
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(run_simulations(parse_args()))
