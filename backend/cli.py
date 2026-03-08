import sys
import os
import asyncio
import uuid
import warnings

# Suppress noisy warnings
warnings.filterwarnings("ignore")

# Add the backend dir to path so we can import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.llm.gateway import LLMGateway
from services.cad_executor import execute_cadquery_safe
from services.ai_service import build_system_prompt, load_examples, extract_intent
from config.settings import settings

def print_header():
    print("")
    print("===============================================================")
    print("                         F E R M E O N                         ")
    print("                  AI Multi-LLM CAD Generator                   ")
    print("===============================================================")
    print("")

async def main():
    print_header()
    
    prompt = input("Describe the part you want to generate:\n> ")
    if not prompt.strip():
        print("Empty prompt. Exiting.")
        return

    print("\nSelect Model:")
    print("1) Ollama Local (qwen2.5-coder:14b) [Default]")
    print("2) Gemini (gemini/gemini-2.0-flash)")
    print("3) Claude (claude-3-5-sonnet-20241022)")
    print("4) OpenAI (gpt-4o)")
    print("Custom: Type exactly the model name (e.g. ollama/llama3)")
    choice = input("> ").strip().lower()

    model = "ollama/qwen2.5-coder:14b"
    if choice == "1": model = "ollama/qwen2.5-coder:14b"
    elif choice == "2": model = "gemini/gemini-2.0-flash"
    elif choice == "3": model = "claude-3-5-sonnet-20241022"
    elif choice == "4": model = "gpt-4o"
    elif choice: model = choice
    
    print(f"\nGenerating using {model}...")

    # Initialize
    gateway = LLMGateway()
    job_id = str(uuid.uuid4())[:8]

    # Parse intent
    intent = extract_intent(prompt, model)
    system_prompt = build_system_prompt(domain=intent.get("domain", "mechanical"))
    examples = load_examples(part_type=intent.get("part_type", "generic"))

    print("Sending prompt to LLM...")
    gen_result = await gateway.generate_with_fallback(
        prompt=prompt,
        preferred_model=model,
        system_prompt=system_prompt,
        examples=examples,
    )

    if not gen_result.get("success"):
        print(f"\n[ERROR] Generation failed: {gen_result.get('error')}")
        return

    code = gen_result["code"]
    model_used = gen_result["model_used"]
    attempts = 1
    
    print(f"\nModel {model_used} provided code. Executing CadQuery...")
    
    # Save code to output dir
    output_dir = os.path.abspath(settings.output_dir)
    os.makedirs(output_dir, exist_ok=True)
    code_path = os.path.join(output_dir, f"{job_id}.py")
    with open(code_path, "w", encoding="utf-8") as f:
        f.write(code)
    
    exec_result = None
    for attempt in range(3):
        exec_result = execute_cadquery_safe(code=code, job_id=job_id)
        if exec_result.get("success"):
            break
        if attempt < 2:
            print(f"Execution error, asking AI to self-correct (Attempt {attempt+1}/3)...")
            correction = await gateway.self_correct(
                original_prompt=prompt,
                failed_code=code,
                error_message=exec_result.get("error"),
                model=model_used,
                system_prompt=system_prompt,
                attempt=attempt+1,
                max_attempts=3
            )
            if correction.get("success"):
                code = correction["code"]
                attempts += 1
                # Update saved code
                with open(code_path, "w", encoding="utf-8") as f:
                    f.write(code)
            else:
                break
                
    if not exec_result or not exec_result.get("success"):
        print(f"\n[ERROR] Failed to generate valid geometry after {attempts} attempts.")
        print(f"Details: {exec_result.get('error') if exec_result else 'Unknown'}")
        print(f"Code saved at: {code_path}")
        return

    paths = exec_result.get("paths", {})
    print(f"\n[SUCCESS] Generation complete after {attempts} attempt(s)!")
    print(f"Python Code: {code_path}")
    for fmt, p in paths.items():
        print(f"{fmt.upper()} File Space: {os.path.abspath(p)}")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nCancelled by user.")
