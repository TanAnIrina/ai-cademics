# evals/eval_journals.py

import ollama
import json
import re

# Modelul folosit pentru a juriza (se recomandă un model mare pentru acuratețe, ex: Llama 3)
JUDGE_MODEL = "gemma3:27b" 

def check_first_person_usage(text: str) -> bool:
    """
    (Rule-Based Eval): Verifică dacă textul conține pronume la persoana I.
    """
    # Folosim \b pentru a căuta cuvinte întregi (case-insensitive)
    first_person_pattern = re.compile(r'\b(i|me|my|mine|we|us|our)\b', re.IGNORECASE)
    matches = first_person_pattern.findall(text)
    
    # Dacă găsim cel puțin 3 pronume, considerăm că este scris la persoana I
    return len(matches) >= 3

def eval_journal_reflection(student_name: str, subject: str, journal_text: str) -> dict:
    """
    (LLM-as-a-Judge Eval): Evaluează dacă jurnalul este o reflexie validă.
    """
    print(f"\n[EVAL 3] Evaluating Journal Reflection for {student_name}...")
    
    # 1. Verificarea bazată pe reguli
    is_first_person = check_first_person_usage(journal_text)
    
    # 2. Verificarea bazată pe LLM (Calitatea conținutului)
    judge_prompt = f"""You are an expert QA Evaluator for an AI educational simulation.
Your task is to analyze a student's journal entry.

STUDENT NAME: {student_name}
LESSON SUBJECT: {subject}
JOURNAL ENTRY:
"{journal_text}"

EVALUATION CRITERIA:
1. Does the text actually reflect on the subject ({subject}), or is it completely off-topic?
2. Does the text contain emotional reflection (e.g., mentioning frustration, happiness, or feelings about the class/teacher/peers)?
3. Does it read like a personal diary entry rather than an encyclopedia article?

Return a STRICT JSON response in this exact format:
{{
    "is_valid_reflection": <boolean>,
    "verdict": "<PASS if it meets ALL criteria, FAIL otherwise>",
    "explanation": "<short explanation of why it passes or fails>"
}}"""

    try:
        response = ollama.chat(
            model=JUDGE_MODEL,
            messages=[{"role": "user", "content": judge_prompt}],
            format="json",
            options={"temperature": 0.0} # Vrem consistență, nu creativitate
        )
        
        llm_result = json.loads(response['message']['content'])
        
        # Combinăm rezultatele (ambele trebuie să treacă)
        final_pass = is_first_person and llm_result.get('is_valid_reflection', False)
        
        result = {
            "first_person_check": is_first_person,
            "reflection_check": llm_result.get('is_valid_reflection', False),
            "final_verdict": "PASS" if final_pass else "FAIL",
            "explanation": llm_result.get('explanation', '')
        }
        
        print("--- Rezultat Eval ---")
        print(f"Scris la persoana I (Regex): {'✅ PASS' if is_first_person else '❌ FAIL'}")
        print(f"Conținut Valid (LLM):        {'✅ PASS' if result['reflection_check'] else '❌ FAIL'}")
        print(f"VERDICT FINAL:               {result['final_verdict']}")
        print(f"Explicație Arbitru:          {result['explanation']}")
        
        return result

    except Exception as e:
        print(f"Eroare la evaluare: {e}")
        return {"final_verdict": "ERROR", "explanation": str(e)}