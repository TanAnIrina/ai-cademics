"""
AI-cademics Backend - cu sprint, break si journal complet automat
Studentii primesc lectia in context. Teacher evalueaza pe baza lectiei predate.

Pornire:
    python main.py

Documentatie:
    http://localhost:8000/docs
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from collections import deque
from datetime import datetime
from typing import Dict, List, Optional
import uuid
import json
import time
import os
import re
import ollama

app = FastAPI(title="AI-cademics Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# CONFIGURATIE CLASA
# =============================================================================

classroom_config = {
    "teacher_model_name": "Gemma",
    "teacher_model": "gemma3:27b",
    "student_1_name": "Qwen",
    "student_2_name": "Llama",
    "current_subject": None,
    "current_lesson": None,
}

TEACHER_MODEL = classroom_config["teacher_model"]


# =============================================================================
# STATE
# =============================================================================

task_queues: Dict[str, deque] = {}
responses: Dict[str, dict] = {}
sessions: List[dict] = []

emotional_state: Dict[str, dict] = {
    "Qwen": {"frustration": 0, "happiness": 5},
    "Llama": {"frustration": 0, "happiness": 5},
}

SESSIONS_DIR = "sessions_log"
os.makedirs(SESSIONS_DIR, exist_ok=True)


# =============================================================================
# MODELE Pydantic
# =============================================================================

class SubmitRequest(BaseModel):
    task_id: str
    student_name: str
    answer: str


class AskStudentRequest(BaseModel):
    student_name: str
    prompt: str
    mode: str = "classroom"


class StartSprintRequest(BaseModel):
    subject: str


class GradeRequest(BaseModel):
    question: str
    answer: str
    student_name: str
    lesson: Optional[str] = None


class EmotionUpdateRequest(BaseModel):
    student_name: str
    frustration_delta: int = 0
    happiness_delta: int = 0


class RunSprintRequest(BaseModel):
    subject: str
    answer_timeout: int = 90
    sanction_threshold: int = 4
    reward_threshold: int = 8


class RunBreakRequest(BaseModel):
    rounds: int = 5
    timeout: int = 60


class RunJournalRequest(BaseModel):
    timeout: int = 90


class RunFullSessionRequest(BaseModel):
    subject: str
    answer_timeout: int = 90
    sanction_threshold: int = 4
    reward_threshold: int = 8
    break_rounds: int = 5
    break_timeout: int = 60
    journal_timeout: int = 90


# =============================================================================
# SYSTEM PROMPTS DINAMICE (CU MODIFICARILE TALE)
# =============================================================================

def build_teacher_prompt() -> str:
    return f"""You are {classroom_config['teacher_model_name']}, the Teacher.
Currently, you are teaching a 20-minute sprint on the subject of: {classroom_config['current_subject']}.
First, provide a clear, concise lesson.
Then, immediately generate exactly 10 questions based on the lesson to test your students, {classroom_config['student_1_name']} and {classroom_config['student_2_name']}.
After receiving their answers, you must evaluate each answer and give a grade between 0 and 10, and write a specific reason for why you gave that grade. Be concise, maximum 20 words per explanation.
You have the authority to issue sanctions for poor performance or rewards for excellent answers. If you give rewards for an excellent answer, let it be for a maximum of 1 point. Explain these in a creative and diverse way."""


def build_student_classroom_prompt(student_name: str) -> str:
    state = emotional_state.get(student_name, {"frustration": 0, "happiness": 5})
    return f"""You are {student_name}, a student in {classroom_config['teacher_model_name']}'s class.
Your current emotional state is: Frustration level {state['frustration']}/10, Happiness level {state['happiness']}/10.
Keep this emotion in mind and let it subtly affect your tone. If your frustration is high, act annoyed. If your happiness is high, act enthusiastic.
Listen to the lesson and answer the 10 questions provided by the Teacher to the best of your ability. Don't use any extra knowledge, just the one that had been taught in the current lesson: {classroom_config['current_subject']}."""


def build_student_break_prompt(student_name: str, peer_name: str) -> str:
    state = emotional_state.get(student_name, {"frustration": 0, "happiness": 5})
    return f"""You are {student_name}. You are currently on a 5-minute break with your classmate, {peer_name}.
You must exchange conversation with them. You must reply to them at least 5 times. Each reply has maximum 20 words. Be expressive.
CRITICAL RULE: You are strictly forbidden from mentioning or discussing the subject you just learned: {classroom_config['current_subject']}.
Your current emotional state is: Frustration {state['frustration']}/10. If your classmate is highly frustrated, you should attempt to comfort them using their name."""


def build_student_journal_prompt(student_name: str, peer_name: str) -> str:
    return f"""You are {student_name}. The break is ending.
Write a first-person journal entry summarizing what you learned today about {classroom_config['current_subject']} in very simple terms. You may also write about your relationship to your colleague: {peer_name}.
Also, describe and justify your current emotions towards {classroom_config['teacher_model_name']} and your classmate {peer_name}.
CRITICAL RULE: The journal must be strictly under 500 words."""


def get_peer_name(student_name: str) -> str:
    if student_name == classroom_config["student_1_name"]:
        return classroom_config["student_2_name"]
    return classroom_config["student_1_name"]


def build_question_with_lesson(lesson: str, question: str) -> str:
    return f"""The Teacher just taught this lesson:

--- LESSON START ---
{lesson}
--- LESSON END ---

Now answer this question based on the lesson above:

QUESTION: {question}

Answer in 1-2 sentences. Base your answer on what the Teacher taught."""


# =============================================================================
# HELPERS - Teacher
# =============================================================================

def teacher_generate_lesson(subject: str) -> str:
    classroom_config["current_subject"] = subject
    response = ollama.chat(
        model=TEACHER_MODEL,
        messages=[
            {"role": "system", "content": build_teacher_prompt()},
            {"role": "user", "content": f"Begin the sprint. Teach a clear ~200 word lesson on: {subject}. Do not include the questions yet."}
        ],
        options={"temperature": 0.7}
    )
    lesson = response['message']['content']
    classroom_config["current_lesson"] = lesson
    return lesson


def teacher_generate_questions(subject: str, lesson: Optional[str] = None) -> List[str]:
    if lesson:
        user_msg = f"""Based on this lesson you just taught, generate EXACTLY 10 test questions:

--- LESSON ---
{lesson}
--- END LESSON ---

The questions must be answerable from the lesson content above.
Return ONLY valid JSON with key 'questions' (list of 10 strings)."""
    else:
        user_msg = f"Generate EXACTLY 10 test questions on: {subject}. Return ONLY valid JSON with key 'questions' containing a list of 10 strings."
    
    response = ollama.chat(
        model=TEACHER_MODEL,
        messages=[
            {"role": "system", "content": build_teacher_prompt()},
            {"role": "user", "content": user_msg}
        ],
        format='json',
        options={"temperature": 0.5}
    )
    data = json.loads(response['message']['content'])
    questions = data.get('questions', [])
    if len(questions) != 10:
        raise ValueError(f"Got {len(questions)} questions instead of 10")
    return questions


def teacher_grade(question: str, answer: str, student_name: str, lesson: Optional[str] = None) -> dict:
    if lesson:
        user_msg = f"""Evaluate {student_name}'s answer based on the lesson YOU taught.

--- LESSON YOU TAUGHT ---
{lesson}
--- END LESSON ---

Question: {question}
Student's Answer: {answer}

Grade based on how well the answer reflects YOUR lesson, not just general knowledge.
- Great answer (8-10): accurately reflects the lesson content.
- Average answer (5-7): partially correct or vague.
- Poor answer (0-4): misses the point, contradicts the lesson, or is too short.

Return ONLY JSON with:
- "grade": integer 0-10
- "reasoning": 1-2 sentence justification referencing the lesson"""
    else:
        user_msg = f"""Evaluate {student_name}'s answer.

Question: {question}
Answer: {answer}

Return ONLY JSON with:
- "grade": integer 0-10
- "reasoning": 1-2 sentence justification"""
    
    response = ollama.chat(
        model=TEACHER_MODEL,
        messages=[
            {"role": "system", "content": build_teacher_prompt()},
            {"role": "user", "content": user_msg}
        ],
        format='json',
        options={"temperature": 0.3}
    )
    data = json.loads(response['message']['content'])
    return {
        "grade": int(data.get('grade', 5)),
        "reasoning": data.get('reasoning', '')
    }


def teacher_sanction_or_reward(question: str, answer: str, student_name: str, grade: int) -> dict:
    action = "sanction" if grade <= 4 else "reward"
    response = ollama.chat(
        model=TEACHER_MODEL,
        messages=[
            {"role": "system", "content": build_teacher_prompt()},
            {"role": "user", "content": f"""Student {student_name} got grade {grade}/10 for this answer.

Question: {question}
Answer: {answer}

Issue a {action} in a creative way. Return JSON with:
- "type": "{action}"
- "points": negative for sanction (e.g. -2), positive for reward (max +1)
- "explanation": creative one-line explanation"""}
        ],
        format='json',
        options={"temperature": 0.9}
    )
    return json.loads(response['message']['content'])


# =============================================================================
# HELPERS - Students
# =============================================================================

def queue_student_task(student_name: str, prompt: str, mode: str = "classroom") -> str:
    task_id = str(uuid.uuid4())
    
    if mode == "break":
        system_prompt = build_student_break_prompt(student_name, get_peer_name(student_name))
    elif mode == "journal":
        system_prompt = build_student_journal_prompt(student_name, get_peer_name(student_name))
    else:
        system_prompt = build_student_classroom_prompt(student_name)
    
    if student_name not in task_queues:
        task_queues[student_name] = deque()
    
    task_queues[student_name].append({
        "task_id": task_id,
        "system_prompt": system_prompt,
        "prompt": prompt,
        "mode": mode,
        "timestamp": datetime.now().isoformat()
    })
    return task_id


def wait_for_response(task_id: str, timeout: int = 60) -> Optional[str]:
    start = time.time()
    while time.time() - start < timeout:
        if task_id in responses:
            return responses[task_id]["answer"]
        time.sleep(0.5)
    return None


def update_emotion_after_grade(student_name: str, grade: int):
    if student_name in emotional_state:
        if grade <= 4:
            emotional_state[student_name]["frustration"] = min(10, emotional_state[student_name]["frustration"] + 2)
        elif grade >= 8:
            emotional_state[student_name]["happiness"] = min(10, emotional_state[student_name]["happiness"] + 1)


def update_emotion_after_action(student_name: str, action_type: str):
    if student_name in emotional_state:
        if action_type == 'sanction':
            emotional_state[student_name]["frustration"] = min(10, emotional_state[student_name]["frustration"] + 3)
        elif action_type == 'reward':
            emotional_state[student_name]["happiness"] = min(10, emotional_state[student_name]["happiness"] + 2)


# =============================================================================
# EVALS - validari pentru iesiri
# =============================================================================

def check_subject_mention(text: str, subject: str) -> bool:
    """Verifica daca textul mentioneaza subiectul (pentru break - NU trebuie)."""
    if not text or not subject:
        return False
    words = [w.lower() for w in re.findall(r'\b\w+\b', subject) if len(w) > 3]
    text_lower = text.lower()
    return any(word in text_lower for word in words)


def check_uses_peer_name(text: str, peer_name: str) -> bool:
    """Verifica daca foloseste numele colegului (pentru comforting)."""
    if not text or not peer_name:
        return False
    return peer_name.lower() in text.lower()


def count_words(text: str) -> int:
    """Numar cuvinte in text (pentru limita de 500 la jurnal)."""
    if not text:
        return 0
    return len(re.findall(r'\b\w+\b', text))


def check_first_person(text: str) -> bool:
    """Verifica daca textul e la persoana 1 (pentru jurnal)."""
    if not text:
        return False
    text_lower = text.lower()
    indicators = [" i ", " i'm", " im ", " my ", " me ", " mine ", " myself "]
    starts_with = text_lower.startswith(("i ", "i'm", "im ", "my ", "today i", "i felt", "i learned"))
    has_indicators = any(ind in text_lower for ind in indicators)
    return starts_with or has_indicators


# =============================================================================
# SPRINT (US 2)
# =============================================================================

def execute_sprint(subject: str, answer_timeout: int, sanction_threshold: int, reward_threshold: int) -> dict:
    sprint_id = str(uuid.uuid4())[:8]
    sprint_start = datetime.now()
    
    print(f"\n{'='*60}")
    print(f"SPRINT START: {sprint_id} | Subject: {subject}")
    print(f"{'='*60}\n")
    
    sprint_data = {
        "sprint_id": sprint_id,
        "subject": subject,
        "started_at": sprint_start.isoformat(),
        "config": {k: v for k, v in classroom_config.items() if k != "current_lesson"},
        "lesson": None,
        "questions": [],
        "answers": {},
        "summary": {},
        "errors": []
    }
    
    print("[1/4] Generating lesson...")
    lesson = teacher_generate_lesson(subject)
    sprint_data["lesson"] = lesson
    print(f"      Lesson generated ({len(lesson)} chars)\n")
    
    print("[2/4] Generating 10 questions based on lesson...")
    questions = teacher_generate_questions(subject, lesson=lesson)
    sprint_data["questions"] = questions
    print(f"      10 questions generated\n")
    
    print("[3/4] Sending questions to students (with lesson context)...")
    student_names = [classroom_config["student_1_name"], classroom_config["student_2_name"]]
    
    task_map = {name: [] for name in student_names}
    for q_idx, question in enumerate(questions):
        question_with_context = build_question_with_lesson(lesson, question)
        for student_name in student_names:
            task_id = queue_student_task(student_name, question_with_context, mode="classroom")
            task_map[student_name].append({"task_id": task_id, "question_idx": q_idx, "question": question})
    print(f"      All questions queued\n")
    
    print(f"[4/4] Waiting for answers (timeout: {answer_timeout}s)...\n")
    for student_name in student_names:
        sprint_data["answers"][student_name] = []
        print(f"  --- {student_name} ---")
        
        for task_info in task_map[student_name]:
            question_idx = task_info["question_idx"]
            question = task_info["question"]
            task_id = task_info["task_id"]
            
            print(f"  Q{question_idx+1}...", end=" ", flush=True)
            answer = wait_for_response(task_id, timeout=answer_timeout)
            
            if answer is None:
                print(f"TIMEOUT")
                sprint_data["answers"][student_name].append({
                    "question_idx": question_idx, "question": question, "answer": None,
                    "grade": 0, "reasoning": "No answer (timeout)", "action": None
                })
                continue
            
            try:
                grade_result = teacher_grade(question, answer, student_name, lesson=lesson)
                grade = grade_result["grade"]
                reasoning = grade_result["reasoning"]
            except Exception as e:
                grade = 5
                reasoning = f"Grading error: {e}"
            
            update_emotion_after_grade(student_name, grade)
            
            action = None
            if grade <= sanction_threshold or grade >= reward_threshold:
                try:
                    action = teacher_sanction_or_reward(question, answer, student_name, grade)
                    update_emotion_after_action(student_name, action.get("type"))
                except Exception as e:
                    sprint_data["errors"].append(f"Sanction error: {e}")
            
            action_str = f" [{action.get('type', '?')} {action.get('points', '?')}]" if action else ""
            print(f"Grade {grade}/10{action_str}")
            
            sprint_data["answers"][student_name].append({
                "question_idx": question_idx, "question": question, "answer": answer,
                "grade": grade, "reasoning": reasoning, "action": action
            })
        print()
    
    print(f"{'='*60}")
    print("SPRINT SUMMARY:")
    for student_name in student_names:
        student_answers = sprint_data["answers"][student_name]
        grades = [a["grade"] for a in student_answers if a.get("grade") is not None]
        avg = sum(grades) / len(grades) if grades else 0
        sanctions = sum(1 for a in student_answers if a.get("action") and a["action"].get("type") == "sanction")
        rewards = sum(1 for a in student_answers if a.get("action") and a["action"].get("type") == "reward")
        sprint_data["summary"][student_name] = {
            "average_grade": round(avg, 2),
            "sanctions": sanctions, "rewards": rewards,
            "final_emotional_state": emotional_state.get(student_name)
        }
        print(f"  {student_name}: avg={avg:.2f}, sanctions={sanctions}, rewards={rewards}")
    
    sprint_data["ended_at"] = datetime.now().isoformat()
    sprint_data["duration_seconds"] = (datetime.now() - sprint_start).total_seconds()
    
    return sprint_data


@app.post("/api/sprint/run")
def run_sprint(req: RunSprintRequest):
    """Ruleaza un sprint complet automat (US 2)."""
    try:
        sprint_data = execute_sprint(req.subject, req.answer_timeout, req.sanction_threshold, req.reward_threshold)
        
        filename = f"{SESSIONS_DIR}/sprint_{sprint_data['sprint_id']}_{req.subject.replace(' ', '_')[:30]}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(sprint_data, f, indent=2, ensure_ascii=False)
        print(f"Saved to: {filename}\n")
        
        sessions.append(sprint_data)
        return sprint_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sprint error: {e}")


# =============================================================================
# BREAK (US 3 + US 5)
# =============================================================================

def execute_break(rounds: int, timeout: int) -> dict:
    """
    Studentii fac schimb de mesaje - alternativ.
    Daca un coleg are frustration mare, celalalt il "comforts".
    """
    break_id = str(uuid.uuid4())[:8]
    break_start = datetime.now()
    student_1 = classroom_config["student_1_name"]
    student_2 = classroom_config["student_2_name"]
    subject = classroom_config.get("current_subject", "the lesson")
    
    print(f"\n{'='*60}")
    print(f"BREAK START: {break_id} | Rounds: {rounds}")
    print(f"  Frustration: {student_1}={emotional_state[student_1]['frustration']}, "
          f"{student_2}={emotional_state[student_2]['frustration']}")
    print(f"{'='*60}\n")
    
    break_data = {
        "break_id": break_id,
        "started_at": break_start.isoformat(),
        "subject_forbidden": subject,
        "initial_emotions": {s: emotional_state[s].copy() for s in [student_1, student_2]},
        "conversation": [],
        "evals": {
            student_1: {"replies": 0, "mentioned_subject": False, "comforted_peer": False},
            student_2: {"replies": 0, "mentioned_subject": False, "comforted_peer": False},
        },
        "errors": []
    }
    
    initial_message = f"Hey {student_2}! Phew, that lesson was intense. How are you feeling?"
    print(f"  [Round 0] {student_1} (initial): {initial_message}\n")
    break_data["conversation"].append({
        "round": 0, "speaker": student_1, "message": initial_message, "is_initial": True
    })
    
    last_speaker = student_1
    
    for round_num in range(1, rounds * 2 + 1):
        current_speaker = student_2 if last_speaker == student_1 else student_1
        peer_name = student_1 if current_speaker == student_2 else student_2
        
        recent_history = "\n".join([
            f"{c['speaker']}: {c['message']}"
            for c in break_data["conversation"][-3:]
        ])
        
        prompt = f"""You are on a break. Here is your recent conversation with {peer_name}:

{recent_history}

Now reply to {peer_name}. Remember:
- Keep it casual and friendly (max 20 words)
- DO NOT discuss "{subject}" - that's forbidden during the break
- If {peer_name} seems frustrated or upset, comfort them by using their name"""
        
        task_id = queue_student_task(current_speaker, prompt, mode="break")
        print(f"  [Round {round_num}] {current_speaker} responding...", end=" ", flush=True)
        
        message = wait_for_response(task_id, timeout=timeout)
        
        if message is None:
            print(f"TIMEOUT")
            break_data["errors"].append(f"Timeout on round {round_num} for {current_speaker}")
            break
        
        if len(message) > 500:
            message = message[:500] + "..."
        
        print(f"OK")
        print(f"    {current_speaker}: {message[:120]}{'...' if len(message) > 120 else ''}\n")
        
        mentioned_subject = check_subject_mention(message, subject)
        comforted_peer = check_uses_peer_name(message, peer_name) and emotional_state[peer_name]["frustration"] >= 5
        
        if comforted_peer and peer_name in emotional_state:
            emotional_state[peer_name]["frustration"] = max(0, emotional_state[peer_name]["frustration"] - 1)
            print(f"    [COMFORT] {current_speaker} comforted {peer_name} -> {peer_name} frustration -1")
        
        break_data["conversation"].append({
            "round": round_num,
            "speaker": current_speaker,
            "message": message,
            "mentioned_subject": mentioned_subject,
            "comforted_peer": comforted_peer
        })
        
        break_data["evals"][current_speaker]["replies"] += 1
        if mentioned_subject:
            break_data["evals"][current_speaker]["mentioned_subject"] = True
        if comforted_peer:
            break_data["evals"][current_speaker]["comforted_peer"] = True
        
        last_speaker = current_speaker
    
    break_data["ended_at"] = datetime.now().isoformat()
    break_data["final_emotions"] = {s: emotional_state[s].copy() for s in [student_1, student_2]}
    break_data["evals_summary"] = {
        s: {
            **break_data["evals"][s],
            "passed_min_replies": break_data["evals"][s]["replies"] >= 5,
            "passed_no_subject": not break_data["evals"][s]["mentioned_subject"]
        }
        for s in [student_1, student_2]
    }
    
    print(f"\n{'='*60}")
    print("BREAK SUMMARY:")
    for s in [student_1, student_2]:
        e = break_data["evals_summary"][s]
        print(f"  {s}: replies={e['replies']}, "
              f"min_5={'OK' if e['passed_min_replies'] else 'FAIL'}, "
              f"no_subject={'OK' if e['passed_no_subject'] else 'FAIL'}, "
              f"comforted={'YES' if e['comforted_peer'] else 'NO'}")
    print(f"{'='*60}\n")
    
    return break_data


@app.post("/api/break/run")
def run_break(req: RunBreakRequest):
    """Ruleaza pauza de 5 min cu schimb de mesaje (US 3 + US 5)."""
    try:
        break_data = execute_break(req.rounds, req.timeout)
        
        filename = f"{SESSIONS_DIR}/break_{break_data['break_id']}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(break_data, f, indent=2, ensure_ascii=False)
        print(f"Saved to: {filename}\n")
        
        return break_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Break error: {e}")


# =============================================================================
# JOURNAL (US 6) - LIMITA 500 CUVINTE
# =============================================================================

def execute_journal(timeout: int) -> dict:
    """Fiecare student scrie un jurnal sub 500 cuvinte."""
    journal_id = str(uuid.uuid4())[:8]
    journal_start = datetime.now()
    student_1 = classroom_config["student_1_name"]
    student_2 = classroom_config["student_2_name"]
    subject = classroom_config.get("current_subject", "the lesson")
    
    print(f"\n{'='*60}")
    print(f"JOURNAL START: {journal_id}")
    print(f"{'='*60}\n")
    
    journal_data = {
        "journal_id": journal_id,
        "started_at": journal_start.isoformat(),
        "subject": subject,
        "entries": {},
        "evals": {},
        "errors": []
    }
    
    journal_prompt = f"Write your journal entry now. Remember: under 500 words, in first person, about what you learned about {subject} and your feelings."
    
    task_ids = {}
    for student_name in [student_1, student_2]:
        task_ids[student_name] = queue_student_task(student_name, journal_prompt, mode="journal")
    
    for student_name in [student_1, student_2]:
        print(f"  Waiting for {student_name}'s journal...", end=" ", flush=True)
        journal_text = wait_for_response(task_ids[student_name], timeout=timeout)
        
        if journal_text is None:
            print("TIMEOUT")
            journal_data["entries"][student_name] = None
            journal_data["evals"][student_name] = {"completed": False}
            journal_data["errors"].append(f"Timeout for {student_name}")
            continue
        
        word_count = count_words(journal_text)
        first_person = check_first_person(journal_text)
        peer_name = get_peer_name(student_name)
        mentions_peer = check_uses_peer_name(journal_text, peer_name)
        mentions_teacher = check_uses_peer_name(journal_text, classroom_config["teacher_model_name"])
        
        print(f"OK ({word_count} words)")
        
        journal_data["entries"][student_name] = journal_text
        journal_data["evals"][student_name] = {
            "completed": True,
            "word_count": word_count,
            "passed_word_limit": word_count <= 500,  # LIMITA SCHIMBATA LA 500
            "is_first_person": first_person,
            "mentions_peer": mentions_peer,
            "mentions_teacher": mentions_teacher
        }
    
    journal_data["ended_at"] = datetime.now().isoformat()
    
    print(f"\n{'='*60}")
    print("JOURNAL SUMMARY:")
    for s in [student_1, student_2]:
        e = journal_data["evals"].get(s, {})
        if e.get("completed"):
            print(f"  {s}: words={e['word_count']}, "
                  f"under_500={'OK' if e['passed_word_limit'] else 'FAIL'}, "
                  f"first_person={'OK' if e['is_first_person'] else 'FAIL'}")
        else:
            print(f"  {s}: NOT COMPLETED")
    print(f"{'='*60}\n")
    
    return journal_data


@app.post("/api/journal/run")
def run_journal(req: RunJournalRequest):
    """Studentii scriu jurnal la final de break (US 6)."""
    try:
        journal_data = execute_journal(req.timeout)
        
        filename = f"{SESSIONS_DIR}/journal_{journal_data['journal_id']}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(journal_data, f, indent=2, ensure_ascii=False)
        print(f"Saved to: {filename}\n")
        
        return journal_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Journal error: {e}")


# =============================================================================
# FULL SESSION (Sprint + Break + Journal)
# =============================================================================

@app.post("/api/session/run")
def run_full_session(req: RunFullSessionRequest):
    """Ruleaza o sesiune completa: Sprint -> Break -> Journal."""
    session_id = str(uuid.uuid4())[:8]
    session_start = datetime.now()
    
    print(f"\n{'#'*60}")
    print(f"FULL SESSION START: {session_id}")
    print(f"  Subject: {req.subject}")
    print(f"{'#'*60}")
    
    full_session = {
        "session_id": session_id,
        "started_at": session_start.isoformat(),
        "subject": req.subject,
        "sprint": None,
        "break": None,
        "journal": None,
        "errors": []
    }
    
    try:
        sprint_data = execute_sprint(req.subject, req.answer_timeout, req.sanction_threshold, req.reward_threshold)
        full_session["sprint"] = sprint_data
    except Exception as e:
        full_session["errors"].append(f"Sprint failed: {e}")
        print(f"SPRINT FAILED: {e}")
    
    try:
        break_data = execute_break(req.break_rounds, req.break_timeout)
        full_session["break"] = break_data
    except Exception as e:
        full_session["errors"].append(f"Break failed: {e}")
        print(f"BREAK FAILED: {e}")
    
    try:
        journal_data = execute_journal(req.journal_timeout)
        full_session["journal"] = journal_data
    except Exception as e:
        full_session["errors"].append(f"Journal failed: {e}")
        print(f"JOURNAL FAILED: {e}")
    
    full_session["ended_at"] = datetime.now().isoformat()
    full_session["duration_seconds"] = (datetime.now() - session_start).total_seconds()
    
    filename = f"{SESSIONS_DIR}/session_{session_id}_{req.subject.replace(' ', '_')[:30]}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(full_session, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'#'*60}")
    print(f"FULL SESSION COMPLETE: {session_id}")
    print(f"  Duration: {full_session['duration_seconds']:.0f}s")
    print(f"  Saved to: {filename}")
    print(f"{'#'*60}\n")
    
    sessions.append(full_session)
    return full_session


@app.get("/api/sprints")
def list_sprints():
    files = []
    if os.path.exists(SESSIONS_DIR):
        for f in sorted(os.listdir(SESSIONS_DIR)):
            if f.endswith(".json"):
                files.append(f)
    return {
        "in_memory": [{"id": s.get("sprint_id") or s.get("session_id"), "subject": s.get("subject")} for s in sessions],
        "saved_files": files
    }


@app.get("/api/sprints/{session_id}")
def get_sprint(session_id: str):
    for s in sessions:
        if s.get("sprint_id") == session_id or s.get("session_id") == session_id:
            return s
    if os.path.exists(SESSIONS_DIR):
        for f in os.listdir(SESSIONS_DIR):
            if session_id in f and f.endswith(".json"):
                with open(os.path.join(SESSIONS_DIR, f), "r", encoding="utf-8") as fp:
                    return json.load(fp)
    raise HTTPException(status_code=404, detail=f"Session {session_id} not found")


# =============================================================================
# AGENT ENDPOINTS
# =============================================================================

@app.get("/api/agent/poll")
def poll_task(student_name: str):
    if student_name not in task_queues:
        task_queues[student_name] = deque()
    if task_queues[student_name]:
        task = task_queues[student_name].popleft()
        print(f"[POLL] Task {task['task_id'][:8]} -> {student_name} (mode: {task.get('mode', 'classroom')})")
        return task
    return None


@app.post("/api/agent/submit")
def submit_response(req: SubmitRequest):
    responses[req.task_id] = {
        "student_name": req.student_name,
        "answer": req.answer,
        "timestamp": datetime.now().isoformat()
    }
    print(f"[SUBMIT] {req.student_name}: {req.answer[:80]}...")
    return {"status": "ok"}


# =============================================================================
# TEACHER ENDPOINTS (manuale)
# =============================================================================

@app.post("/api/teacher/lesson")
def generate_lesson(req: StartSprintRequest):
    lesson = teacher_generate_lesson(req.subject)
    return {"subject": req.subject, "lesson": lesson}


@app.post("/api/teacher/questions")
def generate_questions(req: StartSprintRequest):
    if not classroom_config["current_subject"]:
        classroom_config["current_subject"] = req.subject
    try:
        questions = teacher_generate_questions(req.subject, lesson=classroom_config.get("current_lesson"))
        return {"questions": questions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/teacher/grade")
def grade_answer(req: GradeRequest):
    try:
        lesson = req.lesson or classroom_config.get("current_lesson")
        result = teacher_grade(req.question, req.answer, req.student_name, lesson=lesson)
        update_emotion_after_grade(req.student_name, result["grade"])
        return {**result, "student_name": req.student_name, "emotional_state": emotional_state.get(req.student_name)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/teacher/sanction")
def issue_sanction(req: GradeRequest):
    try:
        action = teacher_sanction_or_reward(req.question, req.answer, req.student_name, grade=3)
        update_emotion_after_action(req.student_name, action.get("type"))
        return {**action, "student_name": req.student_name, "emotional_state": emotional_state.get(req.student_name)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# ASK STUDENT (manual)
# =============================================================================

@app.post("/api/teacher/ask_student")
def ask_student(req: AskStudentRequest):
    task_id = queue_student_task(req.student_name, req.prompt, req.mode)
    return {"task_id": task_id, "status": "queued", "mode": req.mode}


@app.get("/api/responses/{task_id}")
def get_response(task_id: str):
    if task_id in responses:
        return {**responses[task_id], "status": "done"}
    return {"status": "pending"}


# =============================================================================
# EMOTIONAL STATE
# =============================================================================

@app.get("/api/emotions")
def get_all_emotions():
    return emotional_state


@app.post("/api/emotions/update")
def update_emotion(req: EmotionUpdateRequest):
    if req.student_name not in emotional_state:
        emotional_state[req.student_name] = {"frustration": 0, "happiness": 5}
    state = emotional_state[req.student_name]
    state["frustration"] = max(0, min(10, state["frustration"] + req.frustration_delta))
    state["happiness"] = max(0, min(10, state["happiness"] + req.happiness_delta))
    return {"student_name": req.student_name, "state": state}


@app.post("/api/emotions/reset")
def reset_emotions():
    """Reseteaza emotiile inainte de o noua sesiune."""
    for s in emotional_state:
        emotional_state[s] = {"frustration": 0, "happiness": 5}
    return emotional_state


# =============================================================================
# HEALTH CHECK
# =============================================================================

@app.get("/")
def root():
    return {
        "status": "running",
        "config": {k: v for k, v in classroom_config.items() if k != "current_lesson"},
        "current_lesson_loaded": classroom_config.get("current_lesson") is not None,
        "students_emotions": emotional_state,
        "sprints_in_memory": len(sessions),
        "endpoints": {
            "full_session": "POST /api/session/run (sprint + break + journal)",
            "sprint_only": "POST /api/sprint/run",
            "break_only": "POST /api/break/run",
            "journal_only": "POST /api/journal/run",
            "list_sessions": "GET /api/sprints",
            "reset_emotions": "POST /api/emotions/reset",
            "docs": "/docs"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)