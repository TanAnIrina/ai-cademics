# eval_grading.py
#US4

import ollama
import json
from config import JUDGE_MODEL

def eval_grade_reasoning_correlation(grade: int, reasoning: str) -> dict:
    print(f"\n[EVAL 1] Analizare corelație Notă-Feedback...")
    print(f"Notă acordată: {grade}/10")
    print(f"Feedback: '{reasoning}'")

    judge_prompt = f"""You are a strict QA Auditor for an AI grading system.
Your task is to verify if the numerical grade matches the written reasoning.

GRADE GIVEN: {grade}/10
TEACHER'S REASONING: "{reasoning}"

EVALUATION RULES:
- If Grade <= 4: The reasoning MUST be negative, pointing out major flaws.
- If Grade >= 8: The reasoning MUST be highly positive, praising the answer.
- If Grade is between 5 and 7: The reasoning MUST be neutral, mixed, or point out minor flaws.

Return a STRICT JSON response in this exact format:
{{
    "is_correlated": <boolean>,
    "verdict": "<PASS if is_correlated is true, FAIL otherwise>",
    "explanation": "<short explanation of why it passes or fails>"
}}"""

    try:
        response = ollama.chat(
            model=JUDGE_MODEL,
            messages=[{"role": "user", "content": judge_prompt}],
            format="json",
            options={"temperature": 0.0}
        )
        result = json.loads(response['message']['content'])
        print(f"Rezultat: {result.get('verdict')} - {result.get('explanation')}")
        return result
    except Exception as e:
        print(f"Eroare la parsarea JSON-ului: {e}")
        return {"verdict": "ERROR", "explanation": str(e)}