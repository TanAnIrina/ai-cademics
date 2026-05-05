"""
Student Agent - ruleaza pe laptopul colegului
Conecteaza la backend, primeste taskuri cu system_prompt dinamic, raspunde via Ollama local.

Rulare:
    python student_agent.py <NUME> <MODEL> <BACKEND_URL>

Exemple:
    python student_agent.py Qwen qwen3:4b http://100.118.172.91:8000
    python student_agent.py Llama llama3.2:3b http://100.118.172.91:8000
"""

import time
import requests
import ollama
import sys
from datetime import datetime

# =============================================================================
# CONFIGURARE - din argumente comanda
# =============================================================================

STUDENT_NAME = sys.argv[1] if len(sys.argv) > 1 else "Llama"
STUDENT_MODEL = sys.argv[2] if len(sys.argv) > 2 else "llama3.2"
BACKEND_URL = sys.argv[3] if len(sys.argv) > 3 else "http://100.118.172.91:8000"

POLL_INTERVAL = 2  # secunde intre verificari


# =============================================================================
# OLLAMA LOCAL
# =============================================================================

def ask_ollama(system_prompt, user_prompt):
    """
    Trimite prompt la Ollama local.
    System prompt-ul vine de la backend (e construit dinamic in functie de mode).
    """
    response = ollama.chat(
        model=STUDENT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        options={
            "temperature": 0.8,
            "num_ctx": 4096,
            "top_p": 0.9
        }
    )
    return response['message']['content']


# =============================================================================
# COMUNICARE CU BACKEND
# =============================================================================

def fetch_task():
    """Verifica daca backendul are un task pentru noi."""
    try:
        r = requests.get(
            f"{BACKEND_URL}/api/agent/poll",
            params={"student_name": STUDENT_NAME},
            timeout=5
        )
        if r.status_code == 200:
            data = r.json()
            return data if data else None
    except requests.exceptions.RequestException as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Eroare backend: {e}")
    return None


def submit_answer(task_id, answer):
    """Trimite raspunsul inapoi la backend."""
    try:
        r = requests.post(
            f"{BACKEND_URL}/api/agent/submit",
            json={
                "task_id": task_id,
                "student_name": STUDENT_NAME,
                "answer": answer
            },
            timeout=10
        )
        return r.status_code == 200
    except requests.exceptions.RequestException as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Eroare submit: {e}")
        return False


# =============================================================================
# MAIN LOOP
# =============================================================================

def main():
    print("=" * 50)
    print(f"  Student: {STUDENT_NAME}")
    print(f"  Model:   {STUDENT_MODEL}")
    print(f"  Backend: {BACKEND_URL}")
    print("=" * 50)
    
    # Verifica Ollama local
    print("\nVerific Ollama local...")
    try:
        ollama.list()
        print("Ollama OK")
    except Exception as e:
        print(f"EROARE: Ollama nu raspunde local. {e}")
        print("Asigura-te ca Ollama ruleaza ('ollama serve' sau pornit din tray).")
        return
    
    # Verifica modelul
    print(f"Verific modelul {STUDENT_MODEL}...")
    try:
        ollama.chat(
            model=STUDENT_MODEL,
            messages=[{"role": "user", "content": "ok"}],
            options={"num_predict": 5}
        )
        print(f"Model {STUDENT_MODEL} OK")
    except Exception as e:
        print(f"EROARE model: {e}")
        print(f"Ruleaza intai: ollama pull {STUDENT_MODEL}")
        return
    
    # Test backend
    print(f"Verific backend {BACKEND_URL}...")
    try:
        r = requests.get(BACKEND_URL, timeout=5)
        if r.status_code == 200:
            print("Backend OK")
        else:
            print(f"Backend raspunde dar cu cod {r.status_code}")
    except Exception as e:
        print(f"EROARE backend: {e}")
        print("Verifica IP-ul Tailscale al laptopului cu backend.")
        return
    
    print(f"\nAstept taskuri...\n")
    
    while True:
        task = fetch_task()
        
        if task:
            ts = datetime.now().strftime('%H:%M:%S')
            mode = task.get('mode', 'classroom')
            print(f"[{ts}] Task primit ({task['task_id'][:8]}...) mode={mode}")
            print(f"  Prompt: {task['prompt'][:100]}{'...' if len(task['prompt']) > 100 else ''}")
            
            try:
                # System prompt vine de la backend (dinamic)
                system_prompt = task.get('system_prompt', '')
                
                start = time.time()
                answer = ask_ollama(system_prompt, task['prompt'])
                duration = time.time() - start
                
                print(f"  Raspuns ({duration:.1f}s, {len(answer)} chars):")
                print(f"  {answer[:150]}{'...' if len(answer) > 150 else ''}")
                
                if submit_answer(task['task_id'], answer):
                    print(f"  Trimis OK\n")
                else:
                    print(f"  Eroare trimitere\n")
            
            except Exception as e:
                print(f"  Eroare procesare: {e}\n")
        
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nAgent oprit.")