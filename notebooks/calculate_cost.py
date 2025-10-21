import json
from pathlib import Path
import tiktoken

# === 1. 基本配置 ===
PROJECT_ROOT_PATH = "/Users/qiyudai/Documents/Github/Digital-Twin-Simulation"
INPUT_SAMPLE = "text_simulation/text_simulation_input/pid_574_prompt.txt"
OUTPUT_SAMPLE = "text_simulation/text_simulation_output/pid_574/pid_574_sim001/pid_574_sim001_response.json"

# === 2. 模型和单价（以 GPT-4o 为例） ===
MODEL_NAME = "gpt-4o-mini"
PRICE_INPUT_PER_1K = 0.0003   # USD per 1K tokens (input)
PRICE_OUTPUT_PER_1K = 0.0012  # USD per 1K tokens (output)

# === 3. 加载 tiktoken 编码器 ===
# 根据模型自动选择正确的编码器（GPT-4o 兼容 cl100k_base）
enc = tiktoken.encoding_for_model(MODEL_NAME)

def count_tokens(text: str) -> int:
    """Count tokens in a string using tiktoken."""
    return len(enc.encode(text))

# === 4. 读取输入 prompt ===
input_path = Path(PROJECT_ROOT_PATH) / INPUT_SAMPLE
with open(input_path, "r", encoding="utf-8") as f:
    prompt_text = f.read()

# === 5. 读取输出 JSON ===
output_path = Path(PROJECT_ROOT_PATH) / OUTPUT_SAMPLE
with open(output_path, "r", encoding="utf-8") as f:
    output_data = json.load(f)

response_text = output_data.get("response_text", "")

# === 6. 计算 token 数 ===
input_tokens = count_tokens(prompt_text)
output_tokens = count_tokens(response_text)
total_tokens = input_tokens + output_tokens

# === 7. 估算费用 ===
input_cost = input_tokens / 1000 * PRICE_INPUT_PER_1K
output_cost = output_tokens / 1000 * PRICE_OUTPUT_PER_1K
total_cost = input_cost + output_cost

# === 8. 全局 Simulation 估算 ===
NUM_PERSONAS = 2058
NUM_SIM_PER_PERSONA = 100
total_calls = NUM_PERSONAS * NUM_SIM_PER_PERSONA
grand_input_tokens = input_tokens * total_calls
grand_output_tokens = output_tokens * total_calls
grand_cost = total_cost * total_calls

# === 9. 打印结果 ===
print("=== LLM Simulation Cost Estimation ===")
print(f"Model: {MODEL_NAME}")
print(f"Sample input tokens:  {input_tokens:,}")
print(f"Sample output tokens: {output_tokens:,}")
print(f"Per-call estimated cost: ${total_cost:.4f}")
print(f"\n--- Total Simulation Plan ---")
print(f"Personas: {NUM_PERSONAS:,}")
print(f"Simulations per persona: {NUM_SIM_PER_PERSONA:,}")
print(f"Total LLM calls: {total_calls:,}")
print(f"Estimated total cost: ${grand_cost:,.2f}")
print(f"(Input: {grand_input_tokens/1e9:.2f}B tokens, Output: {grand_output_tokens/1e9:.2f}B tokens)")


