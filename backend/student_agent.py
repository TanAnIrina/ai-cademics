"""
ai-cademics — Student Agent

Polls the backend for tasks (questions, break messages, journal entries)
and produces responses using its own Ollama model.

Usage (local):
    python student_agent.py Qwen qwen3:4b
    python student_agent.py Llama llama3.2:3b

Usage (remote — backend on another laptop):
    python student_agent.py Qwen qwen3:4b http://192.168.1.42:8000

Backwards-compatible: if called with just <name>, falls back to a default
model and prints a warning.
"""
import sys
import time
import requests
import ollama

# ── Argument parsing ────────────────────────────────────────────
if len(sys.argv) < 2:
    print("Usage: python student_agent.py <student_name> [model] [backend_url]")
    print("Example: python student_agent.py Qwen qwen3:4b http://localhost:8000")
    sys.exit(1)

student_name = sys.argv[1]

# Per-student default models (fallback if not provided)
DEFAULT_MODELS = {
    "Qwen":  "qwen3:4b",
    "Llama": "llama3.2:3b",
}

if len(sys.argv) >= 3:
    model = sys.argv[2]
else:
    model = DEFAULT_MODELS.get(student_name, "qwen3:4b")
    print(f"[{student_name}] No model arg — defaulting to {model}")

base_url = sys.argv[3] if len(sys.argv) >= 4 else "http://localhost:8000"

print(f"Starting agent for {student_name} using model={model} backend={base_url}")

# Verify model exists in Ollama
try:
    available = ollama.list()
    # Ollama returns either {"models": [{"name": ...}]} or {"models": [{"model": ...}]}
    names = [m.get("name") or m.get("model") for m in available.get("models", [])]
    if model not in names:
        print(f"⚠  Model '{model}' not found in Ollama. Available: {names}")
        print(f"   Run: ollama pull {model}")
except Exception as e:
    print(f"⚠  Could not verify Ollama models: {e}")

# ── Main poll loop ──────────────────────────────────────────────
while True:
    try:
        response = requests.get(
            f"{base_url}/api/agent/poll",
            params={"student_name": student_name},
            timeout=10,
        )
        if response.status_code != 200:
            print(f"[{student_name}] Poll failed: {response.status_code}")
            time.sleep(5)
            continue

        task = response.json()
        if not task:
            time.sleep(1)
            continue

        task_id = task["task_id"]
        # Backend may send 'system_prompt' separately or bundle it into 'prompt'
        system_prompt = task.get("system_prompt", "")
        prompt = task["prompt"]
        mode = task.get("mode", "classroom")

        print(f"[{student_name}] Task {task_id[:8]} (mode={mode})...", end=" ", flush=True)

        # Build messages — only include system if non-empty
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        ollama_response = ollama.chat(
            model=model,
            messages=messages,
            options={"temperature": 0.7},
        )
        answer = ollama_response["message"]["content"]
        print(f"OK ({len(answer)} chars)")

        # Submit back
        submit = requests.post(
            f"{base_url}/api/agent/submit",
            json={
                "task_id": task_id,
                "student_name": student_name,
                "answer": answer,
            },
            timeout=15,
        )
        if submit.status_code != 200:
            print(f"[{student_name}] Submit failed: {submit.text}")

    except KeyboardInterrupt:
        print(f"\n[{student_name}] Stopped by user")
        break
    except requests.exceptions.ConnectionError:
        print(f"[{student_name}] Backend unreachable at {base_url}, retrying in 5s...")
        time.sleep(5)
    except Exception as e:
        print(f"[{student_name}] Error: {e}")
        time.sleep(5)
