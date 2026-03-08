import asyncio
import httpx
import json
import time
from pathlib import Path

# Config
BACKEND_URL = "http://localhost:8000/api/generate"
MODELS_TO_TEST = [
    "ollama/qwen2.5:7b",
    "gemini/gemini-2.0-flash",
    "groq/llama-3.1-70b-versatile"
]
PROMPTS = [
    "A simple 50x30x10mm rectangular plate",
    "An aluminum L-bracket 100x50mm, 3mm thick, with two M6 mounting holes",
    "A cylindrical pipe flange, OD 80mm, ID 30mm, 10mm thick, with 4 equally spaced bolt holes of 6mm diameter"
]
OUTPUT_FILE = "benchmark_results.json"

async def run_test(client: httpx.AsyncClient, model: str, prompt: str):
    print(f"Testing {model} -> '{prompt[:40]}...'")
    start_time = time.time()
    
    try:
        resp = await client.post(
            BACKEND_URL,
            json={"prompt": prompt, "model": model, "enable_fallback": False, "domain": "mechanical"},
            timeout=180.0
        )
        duration = time.time() - start_time
        
        if resp.status_code != 200:
            return {"model": model, "prompt": prompt, "success": False, "error": resp.text, "time_s": duration}
            
        data = resp.json()
        stats = data.get("mesh_stats", {})
        
        return {
            "model": model,
            "prompt": prompt,
            "success": True,
            "time_s": duration,
            "attempts": data.get("attempts"),
            "cost_usd": data.get("cost_usd"),
            "mesh": {
                "watertight": stats.get("is_watertight"),
                "faces": stats.get("face_count"),
                "volume": stats.get("volume_mm3")
            }
        }
    except Exception as e:
        duration = time.time() - start_time
        return {"model": model, "prompt": prompt, "success": False, "error": str(e), "time_s": duration}

async def main():
    print(f"Starting Fermeon Benchmark: {len(MODELS_TO_TEST)} models, {len(PROMPTS)} prompts")
    results = []
    
    async with httpx.AsyncClient() as client:
        # Check backend is up
        try:
            await client.get("http://localhost:8000/health")
        except:
            print("ERROR: Backend is not running at localhost:8000")
            print("Start the backend first: cd backend && uvicorn main:app")
            return

        for model in MODELS_TO_TEST:
            for prompt in PROMPTS:
                res = await run_test(client, model, prompt)
                results.append(res)
                
    # Save results
    with open(OUTPUT_FILE, "w") as f:
        json.dump(results, f, indent=2)
        
    print(f"\nBenchmark complete. Saved to {OUTPUT_FILE}")
    
    # Print summary
    print("\n--- Summary ---")
    for r in results:
        status = "✅ PASS" if r.get("success") else "❌ FAIL"
        wt = "🚰 Watertight" if r.get("mesh", {}).get("watertight") else "⚠️ Leaky/Fail"
        t = f"{r.get('time_s', 0):.1f}s"
        print(f"{status} | {r['model']:<25} | {t:>5} | {wt} | {r['prompt'][:35]}...")

if __name__ == "__main__":
    asyncio.run(main())
