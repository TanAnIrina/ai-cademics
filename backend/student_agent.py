import requests
import time
import ollama
import sys

if len(sys.argv) < 2:
    print("Usage: python student_agent.py <student_name>")
    sys.exit(1)

student_name = sys.argv[1]
base_url = "http://localhost:8000"

print(f"Starting agent for {student_name}")

while True:
    try:
        # Poll for task
        response = requests.get(f"{base_url}/api/agent/poll?student_name={student_name}")
        if response.status_code == 200:
            task = response.json()
            if task:
                task_id = task['task_id']
                system_prompt = task['system_prompt']
                prompt = task['prompt']
                mode = task.get('mode', 'classroom')

                print(f"[{student_name}] Processing task {task_id[:8]} (mode: {mode})")

                # Generate response using Ollama
                ollama_response = ollama.chat(
                    model="gemma3:27b",  # Use the same model or specify per student
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    options={"temperature": 0.7}
                )
                answer = ollama_response['message']['content']

                # Submit response
                submit_data = {
                    "task_id": task_id,
                    "student_name": student_name,
                    "answer": answer
                }
                submit_response = requests.post(f"{base_url}/api/agent/submit", json=submit_data)
                if submit_response.status_code == 200:
                    print(f"[{student_name}] Submitted response for task {task_id[:8]}")
                else:
                    print(f"[{student_name}] Failed to submit: {submit_response.text}")
            else:
                time.sleep(1)  # No task, wait
        else:
            print(f"[{student_name}] Poll failed: {response.status_code}")
            time.sleep(5)
    except Exception as e:
        print(f"[{student_name}] Error: {e}")
        time.sleep(5)