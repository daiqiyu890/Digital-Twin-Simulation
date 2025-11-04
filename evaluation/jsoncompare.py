import json
from pathlib import Path

def load_json(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Failed to load {path}: {e}")
        return None

def summarize_structure(obj, prefix=""):
    """
    递归提取键名结构，输出集合
    """
    keys = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            keys.add(prefix + k)
            keys |= summarize_structure(v, prefix + k + ".")
    elif isinstance(obj, list) and obj:
        # 看第一个元素的结构（假设同构）
        keys |= summarize_structure(obj[0], prefix + "[]:")
    return keys

def compare_json_structures(success_path, fail_path):
    success = load_json(success_path)
    fail = load_json(fail_path)
    if success is None or fail is None:
        return

    success_keys = summarize_structure(success)
    fail_keys = summarize_structure(fail)

    common = success_keys & fail_keys
    only_success = success_keys - fail_keys
    only_fail = fail_keys - success_keys

    print(f"✅ {success_path.name} keys: {len(success_keys)}")
    print(f"❌ {fail_path.name} keys: {len(fail_keys)}")
    print(f"🔗 common keys: {len(common)}")
    print(f"⚙️ unique to success ({len(only_success)}): {sorted(list(only_success))[:20]}")
    print(f"⚙️ unique to fail ({len(only_fail)}): {sorted(list(only_fail))[:20]}")

    # 顶层类型差异
    print("\nTop-level types:")
    print(f"{success_path.name}: {type(success)}")
    print(f"{fail_path.name}: {type(fail)}")

if __name__ == "__main__":
    success_json = Path("/scratch/qd2177/research/Digital-Twin-Simulation/text_simulation/text_simulation_output/answer_blocks_llm_imputed/pid_121/pid_121_sim001/pid_121_wave4_Q_wave4_A.json")
    fail_json = Path("/scratch/qd2177/research/Digital-Twin-Simulation/text_simulation/text_simulation_output/answer_blocks_llm_imputed/pid_122/pid_122_sim001/pid_122_sim001_wave4_Q_wave4_A.json")
    compare_json_structures(success_json, fail_json)
