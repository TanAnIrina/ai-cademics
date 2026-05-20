# eval_emotions.py

import ollama
import json
from config import JUDGE_MODEL

def eval_emotional_accuracy(frustration_level: int, student_text: str) -> dict:
    print(f"\n[EVAL 2] Analizare Acuratețe Emoțională...")
    print(f"Nivel Frustrare Țintă: {frustration_level}/10")
    print(f"Text Generat: '{student_text}'")

    judge_prompt = f"""You are a strict QA Auditor for an AI roleplay system.
Your task is to verify if the student's text accurately reflects their assigned frustration level.

TARGET FRUSTRATION LEVEL: {frustration_level}/10
STUDENT TEXT: "{student_text}"

EVALUATION RULES:
- If Target Level >= 8: The text MUST sound angry, highly annoyed, cynical, or uncooperative.
- If Target Level <= 3: The text MUST sound calm, positive, or cooperative.
- If Target Level is between 4 and 7: The text MUST sound neutral or mildly irritated.

Return a STRICT JSON response in this exact format:
{{
    "matches_emotion": <boolean>,
    "verdict": "<PASS if matches_emotion is true, FAIL otherwise>",
    "explanation": "<short explanation analyzing the tone of the text>"
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