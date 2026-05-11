"""
AI-cademics Backend - VERSION 3: Sprint + Break + SQLite + Achievements + WEBSOCKET

NEW IN V3 (on top of V2):
- WebSocket endpoint /ws for real-time event broadcasting
- Live events: sprint_started, lesson_complete, grade_assigned, achievement_unlocked, etc
- Dashboard can connect and see EVERY action in real-time
- Event history kept for late-joining clients (last 100 events)

INHERITED FROM V2:
- 15 achievement badges with auto-detection
- Cumulative achievements

INHERITED FROM V1:
- Database persistence

Pornire:
    python main.py

WebSocket:
    ws://localhost:8000/ws
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
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

# NEW: Database module
import database as db
# NEW IN V2: Achievements module
import achievements as ach
# NEW IN V3: WebSocket streaming module
import streaming as ws
import live_state as live

app = FastAPI(title="AI-cademics Backend", version="3.0")

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
# STATE (in-memory only - active session)
# =============================================================================

task_queues: Dict[str, deque] = {}
responses: Dict[str, dict] = {}

emotional_state: Dict[str, dict] = {
    "Qwen": {"frustration": 0, "happiness": 5},
    "Llama": {"frustration": 0, "happiness": 5},
}

run_control = {
    "cancel_requested": False,
    "active_sprint_id": None,
    "active_break_id": None,
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


class RunFullSessionRequest(BaseModel):
    subject: str
    answer_timeout: int = 90
    sanction_threshold: int = 4
    reward_threshold: int = 8
    break_rounds: int = 5
    break_timeout: int = 60


class ResetSprintRequest(BaseModel):
    reset_emotions: bool = False


# =============================================================================
# SYSTEM PROMPTS
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
# TEACHER HELPERS
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

Grade based on how well the answer reflects YOUR lesson.
- Great answer (8-10): accurately reflects the lesson content.
- Average answer (5-7): partially correct or vague.
- Poor answer (0-4): misses the point or contradicts the lesson.

Return ONLY JSON with:
- "grade": integer 0-10
- "reasoning": 1-2 sentence justification"""
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
# STUDENT HELPERS
# =============================================================================

def queue_student_task(student_name: str, prompt: str, mode: str = "classroom") -> str:
    task_id = str(uuid.uuid4())
    
    if mode == "break":
        system_prompt = build_student_break_prompt(student_name, get_peer_name(student_name))
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
        if run_control["cancel_requested"]:
            return None
        if task_id in responses:
            return responses[task_id]["answer"]
        time.sleep(0.5)
    return None


def update_emotion_after_grade(student_name: str, grade: int, sprint_id: str = ""):
    if student_name not in emotional_state:
        return
    
    if grade <= 4:
        emotional_state[student_name]["frustration"] = min(10, emotional_state[student_name]["frustration"] + 2)
    elif grade >= 8:
        emotional_state[student_name]["happiness"] = min(10, emotional_state[student_name]["happiness"] + 1)
    
    # NEW: persist to DB (skip if run was cancelled)
    state = emotional_state[student_name]
    if not run_control["cancel_requested"]:
        db.record_emotion(student_name, state["frustration"], state["happiness"], sprint_id, f"After grade {grade}")
    # NEW IN V3: broadcast to WebSocket
    ws.manager.broadcast_sync(ws.event_emotion_updated(
        student_name, state["frustration"], state["happiness"], f"Got {grade}/10"
    ))


def update_emotion_after_action(student_name: str, action_type: str, sprint_id: str = ""):
    if student_name not in emotional_state:
        return
    
    if action_type == 'sanction':
        emotional_state[student_name]["frustration"] = min(10, emotional_state[student_name]["frustration"] + 3)
    elif action_type == 'reward':
        emotional_state[student_name]["happiness"] = min(10, emotional_state[student_name]["happiness"] + 2)
    
    # NEW: persist to DB (skip if run was cancelled)
    state = emotional_state[student_name]
    if not run_control["cancel_requested"]:
        db.record_emotion(student_name, state["frustration"], state["happiness"], sprint_id, f"After {action_type}")
    # NEW IN V3: broadcast to WebSocket
    ws.manager.broadcast_sync(ws.event_emotion_updated(
        student_name, state["frustration"], state["happiness"], action_type
    ))


# =============================================================================
# EVALS
# =============================================================================

def check_subject_mention(text: str, subject: str) -> bool:
    if not text or not subject:
        return False
    words = [w.lower() for w in re.findall(r'\b\w+\b', subject) if len(w) > 3]
    text_lower = text.lower()
    return any(word in text_lower for word in words)


def check_uses_peer_name(text: str, peer_name: str) -> bool:
    if not text or not peer_name:
        return False
    return peer_name.lower() in text.lower()


# =============================================================================
# SPRINT (US 2)
# =============================================================================

def execute_sprint(subject: str, answer_timeout: int, sanction_threshold: int, reward_threshold: int) -> dict:
    sprint_id = str(uuid.uuid4())[:8]
    sprint_start = datetime.now()
    run_control["cancel_requested"] = False
    run_control["active_sprint_id"] = sprint_id
    
    print(f"\n{'='*60}")
    print(f"SPRINT START: {sprint_id} | Subject: {subject}")
    print(f"{'='*60}\n")
    
    # NEW IN V3: broadcast sprint started
    ws.manager.broadcast_sync(ws.event_sprint_started(sprint_id, subject))
    
    # LIVE: notify start
    live.start_sprint(sprint_id, subject, total_questions=10, num_students=2)
    
    sprint_data = {
        "sprint_id": sprint_id,
        "subject": subject,
        "started_at": sprint_start.isoformat(),
        "config": {k: v for k, v in classroom_config.items() if k != "current_lesson"},
        "lesson": None,
        "questions": [],
        "answers": {},
        "summary": {},
        "errors": [],
        "newly_unlocked_achievements": {}  # NEW IN V2
    }

    # NEW IN V1.1: pre-save sprint stub so FK-referenced inserts work mid-sprint
    # (record_emotion, save_sprint, etc. all reference sprint_id as a FK)
    try:
        db.create_sprint_stub(sprint_id, subject, sprint_start.isoformat())
    except Exception as e:
        print(f"  ! Could not pre-save sprint stub: {e}")
    
    print("[1/4] Generating lesson...")
    lesson = teacher_generate_lesson(subject)
    if run_control["cancel_requested"]:
        sprint_data["cancelled"] = True
        return sprint_data
    sprint_data["lesson"] = lesson
    print(f"      Lesson generated ({len(lesson)} chars)\n")
    
    live.lesson_generated(len(lesson))
    
    # NEW IN V3: broadcast lesson complete
    ws.manager.broadcast_sync(ws.event_lesson_complete(lesson, sprint_id, subject))
    
    print("[2/4] Generating 10 questions based on lesson...")
    questions = teacher_generate_questions(subject, lesson=lesson)
    if run_control["cancel_requested"]:
        sprint_data["cancelled"] = True
        return sprint_data
    sprint_data["questions"] = questions
    # NEW IN V3: broadcast questions
    ws.manager.broadcast_sync(ws.event_questions_generated(questions, sprint_id))
    print(f"      10 questions generated\n")
    
    live.questions_generated(len(questions))
    
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
        if run_control["cancel_requested"]:
            sprint_data["cancelled"] = True
            return sprint_data
        sprint_data["answers"][student_name] = []
        print(f"  --- {student_name} ---")
        
        for task_info in task_map[student_name]:
            if run_control["cancel_requested"]:
                sprint_data["cancelled"] = True
                return sprint_data
            question_idx = task_info["question_idx"]
            question = task_info["question"]
            task_id = task_info["task_id"]
            
            # NEW IN V3: broadcast student thinking
            ws.manager.broadcast_sync(ws.event_student_thinking(student_name, question_idx, question))
            
            print(f"  Q{question_idx+1}...", end=" ", flush=True)
            answer = wait_for_response(task_id, timeout=answer_timeout)
            if run_control["cancel_requested"]:
                sprint_data["cancelled"] = True
                return sprint_data
            
            if answer is None:
                print(f"TIMEOUT")
                live.tick_timeout(student_name, question_idx)
                sprint_data["answers"][student_name].append({
                    "question_idx": question_idx, "question": question, "answer": None,
                    "grade": 0, "reasoning": "No answer (timeout)", "action": None
                })
                continue
            
            # NEW IN V3: broadcast answer received
            ws.manager.broadcast_sync(ws.event_answer_received(student_name, question_idx, answer))
            
            try:
                grade_result = teacher_grade(question, answer, student_name, lesson=lesson)
                grade = grade_result["grade"]
                reasoning = grade_result["reasoning"]
            except Exception as e:
                grade = 5
                reasoning = f"Grading error: {e}"
            
            # NEW IN V3: broadcast grade
            ws.manager.broadcast_sync(ws.event_grade_assigned(student_name, question_idx, grade, reasoning))
            update_emotion_after_grade(student_name, grade, sprint_id)
            
            action = None
            if grade <= sanction_threshold or grade >= reward_threshold:
                try:
                    action = teacher_sanction_or_reward(question, answer, student_name, grade)
                    update_emotion_after_action(student_name, action.get("type"), sprint_id)
                    # NEW IN V3: broadcast action
                    ws.manager.broadcast_sync(ws.event_action_issued(
                        student_name, action.get("type"), action.get("points", 0),
                        action.get("explanation", "")
                    ))
                except Exception as e:
                    sprint_data["errors"].append(f"Sanction error: {e}")
            
            action_str = f" [{action.get('type', '?')} {action.get('points', '?')}]" if action else ""
            print(f"Grade {grade}/10{action_str}")
            
            live.tick_answer(student_name, question_idx, question, grade, reasoning, action)
            
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
    
    # NEW: SAVE TO DATABASE (skip if run cancelled)
    if not run_control["cancel_requested"]:
        try:
            db.save_sprint(sprint_data)
            print(f"  -> Sprint saved to DB")
        except Exception as e:
            print(f"  ! DB save error: {e}")
            sprint_data["errors"].append(f"DB save: {e}")
    
    # NEW IN V2: CHECK ACHIEVEMENTS
    for student_name in student_names:
        if run_control["cancel_requested"]:
            break
        all_new = []
        # Sprint-specific achievements (perfect score, comeback, etc)
        sprint_aches = ach.check_sprint_achievements(student_name, sprint_data)
        all_new.extend(sprint_aches)
        # Cumulative achievements (10 sprints, etc)
        cumulative_aches = ach.check_cumulative_achievements(student_name, sprint_id)
        all_new.extend(cumulative_aches)
        
        sprint_data["newly_unlocked_achievements"][student_name] = all_new
        
        for badge in all_new:
            print(f"  ACHIEVEMENT! {student_name} unlocked: {badge['title']}")
            live.achievement_unlocked(student_name, badge)
            # NEW IN V3: broadcast achievement
            ws.manager.broadcast_sync(ws.event_achievement_unlocked(student_name, badge))
    
    # NEW IN V3: broadcast sprint completed
    ws.manager.broadcast_sync(ws.event_sprint_completed(sprint_id, sprint_data["summary"]))
    
    # LIVE: notify completion so frontend exits 'sprint_running' state
    live.end_sprint(sprint_id, sprint_data.get("summary", {}))
    
    return sprint_data


@app.post("/api/sprint/run")
def run_sprint(background_tasks: BackgroundTasks, req: RunSprintRequest):
    """Ruleaza un sprint complet automat (US 2) - cu DB save - in background."""
    background_tasks.add_task(run_sprint_sync, req)
    return {"status": "started", "message": "Sprint started in background"}


def run_sprint_sync(req: RunSprintRequest):
    """Ruleaza un sprint complet automat (US 2) - cu DB save."""
    try:
        sprint_data = execute_sprint(req.subject, req.answer_timeout, req.sanction_threshold, req.reward_threshold)
        if sprint_data.get("cancelled"):
            db.delete_sprint_progress(sprint_data.get("sprint_id"))
            run_control["active_sprint_id"] = None
            run_control["cancel_requested"] = False
            live.reset()  # LIVE: clear so frontend /api/live returns idle
            return {"status": "cancelled", "sprint_id": sprint_data.get("sprint_id")}
        
        # JSON file backup (still saved)
        filename = f"{SESSIONS_DIR}/sprint_{sprint_data['sprint_id']}_{req.subject.replace(' ', '_')[:30]}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(sprint_data, f, indent=2, ensure_ascii=False)
        
        live.end_session()  # LIVE: notify success completion -> idle
        return sprint_data
    except Exception as e:
        live.reset()  # LIVE: clear on error too
        print(f"Sprint error: {e}")
        # Since it's background, can't raise HTTPException, just print


@app.post("/api/sprint/reset")
def reset_sprint(req: ResetSprintRequest = ResetSprintRequest()):
    """
    Reseteaza starea activa de sprint din memorie:
    - subiect/lectie curenta
    - cozi task-uri studenti
    - raspunsuri task-uri
    Optional: reset emotii la baseline.
    """
    print("session stopped")
    run_control["cancel_requested"] = True
    active_sprint_id = run_control.get("active_sprint_id")

    classroom_config["current_subject"] = None
    classroom_config["current_lesson"] = None

    task_queues.clear()
    responses.clear()

    if active_sprint_id:
        db.delete_sprint_progress(active_sprint_id)
    run_control["active_sprint_id"] = None
    run_control["active_break_id"] = None

    # LIVE: clear so /api/live returns idle immediately;
    # the frontend's live panel will disappear on the next poll.
    live.reset()

    if req.reset_emotions:
        for student in emotional_state:
            emotional_state[student] = {"frustration": 0, "happiness": 5}
            db.record_emotion(student, 0, 5, context="Sprint reset")
            ws.manager.broadcast_sync(ws.event_emotion_updated(student, 0, 5, "Sprint reset"))

    return {
        "status": "ok",
        "message": "Sprint state reset.",
        "current_subject": classroom_config["current_subject"],
        "current_lesson_loaded": classroom_config["current_lesson"] is not None,
        "queued_students": list(task_queues.keys()),
        "responses_total": len(responses),
        "emotions_reset": req.reset_emotions,
        "cancel_requested": True,
        "deleted_sprint_id": active_sprint_id
    }


# =============================================================================
# BREAK (US 3 + US 5)
# =============================================================================

def execute_break(rounds: int, timeout: int, sprint_id: Optional[str] = None) -> dict:
    """Studentii fac schimb de mesaje - alternativ."""
    break_id = str(uuid.uuid4())[:8]
    break_start = datetime.now()
    run_control["active_break_id"] = break_id
    student_1 = classroom_config["student_1_name"]
    student_2 = classroom_config["student_2_name"]
    subject = classroom_config.get("current_subject", "the lesson")
    
    print(f"\n{'='*60}")
    print(f"BREAK START: {break_id} | Rounds: {rounds}")
    print(f"  Frustration: {student_1}={emotional_state[student_1]['frustration']}, "
          f"{student_2}={emotional_state[student_2]['frustration']}")
    print(f"{'='*60}\n")
    
    live.start_break(break_id, total_rounds=rounds, forbidden_subject=subject)
    
    # NEW IN V3: broadcast break started
    ws.manager.broadcast_sync(ws.event_break_started(break_id, sprint_id))
    
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
    
    live.tick_break_message(student_1, initial_message, mentioned_subject=False, comforted_peer=False)

    # NEW IN V3: broadcast initial message
    ws.manager.broadcast_sync(ws.event_break_message(student_1, initial_message, 0))
    
    last_speaker = student_1
    
    for round_num in range(1, rounds * 2 + 1):
        if run_control["cancel_requested"]:
            break_data["cancelled"] = True
            return break_data
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
        if run_control["cancel_requested"]:
            break_data["cancelled"] = True
            return break_data
        
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
            # NEW: record DB
            if not run_control["cancel_requested"]:
                db.record_emotion(peer_name, emotional_state[peer_name]["frustration"],
                                    emotional_state[peer_name]["happiness"], sprint_id, "Comforted by peer")
            # NEW IN V3: broadcast emotion update
            ws.manager.broadcast_sync(ws.event_emotion_updated(
                peer_name, emotional_state[peer_name]["frustration"],
                emotional_state[peer_name]["happiness"], f"Comforted by {current_speaker}"
            ))
        
        # NEW IN V3: broadcast break message
        ws.manager.broadcast_sync(ws.event_break_message(
            current_speaker, message, round_num, mentioned_subject, comforted_peer
        ))
        
        break_data["conversation"].append({
            "round": round_num,
            "speaker": current_speaker,
            "message": message,
            "mentioned_subject": mentioned_subject,
            "comforted_peer": comforted_peer
        })
        
        live.tick_break_message(current_speaker, message, mentioned_subject, comforted_peer)
        
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
    
    # NEW: SAVE TO DATABASE
    if not run_control["cancel_requested"]:
        try:
            db.save_break(break_data, sprint_id)
            print(f"  -> Break saved to DB")
        except Exception as e:
            print(f"  ! DB save error: {e}")
    
    # NEW IN V2: CHECK BREAK ACHIEVEMENTS
    for student_name in [student_1, student_2]:
        if run_control["cancel_requested"]:
            break
        peer = student_2 if student_name == student_1 else student_1
        new_aches = ach.check_break_achievements(student_name, break_data, peer)
        for badge in new_aches:
            print(f"  ACHIEVEMENT! {student_name} unlocked: {badge['title']}")
            # NEW IN V3: broadcast achievement
            ws.manager.broadcast_sync(ws.event_achievement_unlocked(student_name, badge))
    
    print(f"\n{'='*60}")
    print("BREAK SUMMARY:")
    for s in [student_1, student_2]:
        e = break_data["evals_summary"][s]
        print(f"  {s}: replies={e['replies']}, "
              f"min_5={'OK' if e['passed_min_replies'] else 'FAIL'}, "
              f"no_subject={'OK' if e['passed_no_subject'] else 'FAIL'}, "
              f"comforted={'YES' if e['comforted_peer'] else 'NO'}")
    print(f"{'='*60}\n")
    
    # NEW IN V3: broadcast break completed
    ws.manager.broadcast_sync(ws.event_break_completed(break_id, break_data["evals_summary"]))
    
    # LIVE: notify completion so frontend exits 'break_running' state
    live.end_break(break_id)
    
    return break_data


@app.post("/api/break/run")
def run_break(background_tasks: BackgroundTasks, req: RunBreakRequest):
    """Ruleaza pauza cu schimb de mesaje (US 3 + US 5) + DB save - in background."""
    background_tasks.add_task(run_break_sync, req)
    return {"status": "started", "message": "Break started in background"}


def run_break_sync(req: RunBreakRequest):
    """Ruleaza pauza cu schimb de mesaje (US 3 + US 5) + DB save."""
    try:
        break_data = execute_break(req.rounds, req.timeout)
        if break_data.get("cancelled"):
            live.reset()  # LIVE: clear
            return {"status": "cancelled"}
        
        filename = f"{SESSIONS_DIR}/break_{break_data['break_id']}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(break_data, f, indent=2, ensure_ascii=False)
        
        live.end_session()  # LIVE: notify success -> idle
        return break_data
    except Exception as e:
        live.reset()  # LIVE: clear on error
        print(f"Break error: {e}")


# =============================================================================
# FULL SESSION
# =============================================================================

@app.post("/api/session/run")
def run_full_session(background_tasks: BackgroundTasks, req: RunFullSessionRequest):
    """Ruleaza o sesiune completa: Sprint -> Break - in background."""
    background_tasks.add_task(run_full_session_sync, req)
    return {"status": "started", "message": "Full session started in background"}


def run_full_session_sync(req: RunFullSessionRequest):
    """Ruleaza o sesiune completa: Sprint -> Break."""
    session_id = str(uuid.uuid4())[:8]
    session_start = datetime.now()
    
    print(f"\n{'#'*60}")
    print(f"FULL SESSION START: {session_id}")
    print(f"  Subject: {req.subject}")
    print(f"{'#'*60}")
    
    # NEW IN V3: broadcast session started
    ws.manager.broadcast_sync(ws.event_session_started(session_id, req.subject))
    
    full_session = {
        "session_id": session_id,
        "started_at": session_start.isoformat(),
        "subject": req.subject,
        "sprint": None,
        "break": None,
        "errors": []
    }
    
    sprint_id = None
    try:
        sprint_data = execute_sprint(req.subject, req.answer_timeout, req.sanction_threshold, req.reward_threshold)
        full_session["sprint"] = sprint_data
        sprint_id = sprint_data.get("sprint_id")
    except Exception as e:
        full_session["errors"].append(f"Sprint failed: {e}")
        print(f"SPRINT FAILED: {e}")
        live.end_session()  # NEW: notify frontend that we're done (with error)
    
    try:
        break_data = execute_break(req.break_rounds, req.break_timeout, sprint_id=sprint_id)
        full_session["break"] = break_data
    except Exception as e:
        full_session["errors"].append(f"Break failed: {e}")
        print(f"BREAK FAILED: {e}")
    
    full_session["ended_at"] = datetime.now().isoformat()
    full_session["duration_seconds"] = (datetime.now() - session_start).total_seconds()
    
    filename = f"{SESSIONS_DIR}/session_{session_id}_{req.subject.replace(' ', '_')[:30]}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(full_session, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'#'*60}")
    print(f"FULL SESSION COMPLETE: {session_id}")
    print(f"  Duration: {full_session['duration_seconds']:.0f}s")
    print(f"{'#'*60}\n")
    
    # NEW IN V3: broadcast session completed
    ws.manager.broadcast_sync(ws.event_session_completed(session_id, full_session["duration_seconds"]))
    
    # LIVE: notify session completion so frontend exits running state
    live.end_session()
    
    return full_session


# =============================================================================
# NEW IN V3: WEBSOCKET ENDPOINT
# =============================================================================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Real-time event stream for dashboard."""
    await ws.manager.connect(websocket)
    try:
        while True:
            # Keep connection alive, listen for ping/messages
            data = await websocket.receive_text()
            await websocket.send_json({"type": "pong", "data": data})
    except WebSocketDisconnect:
        ws.manager.disconnect(websocket)
    except Exception as e:
        print(f"[WS] Error: {e}")
        ws.manager.disconnect(websocket)


# =============================================================================
# NEW IN V1: DATABASE QUERY ENDPOINTS
# =============================================================================

@app.get("/api/leaderboard")
def get_leaderboard():
    """Get leaderboard sorted by average grade."""
    return db.get_leaderboard()


@app.get("/api/students")
def get_all_students():
    """Get all students with stats."""
    return db.get_all_students()


@app.get("/api/students/{student_name}")
def get_student_detail(student_name: str):
    """Get student details + badges + progression."""
    student = db.get_student(student_name)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    return {
        **student,
        "badges": ach.get_student_badges(student_name),  # NEW IN V2
        "locked_achievements": ach.get_locked_achievements(student_name),  # NEW IN V2
        "progression": db.get_student_progression(student_name),
        "current_emotions": emotional_state.get(student_name, {})
    }


# NEW IN V2: Badge endpoints
@app.get("/api/students/{student_name}/badges")
def get_student_badges(student_name: str):
    """Get all unlocked + locked badges for student."""
    return {
        "unlocked": ach.get_student_badges(student_name),
        "locked": ach.get_locked_achievements(student_name)
    }


@app.get("/api/achievements")
def get_all_achievements():
    """Get all available achievements (for UI display)."""
    return ach.get_all_achievements()


@app.get("/api/students/{student_name}/progression")
def get_student_progression(student_name: str):
    """Get student's grade progression over time."""
    return db.get_student_progression(student_name)


@app.get("/api/students/{student_name}/emotions/history")
def get_emotion_history(student_name: str, limit: int = 100):
    """Get emotion changes over time."""
    return db.get_emotion_history(student_name, limit)


@app.get("/api/stats")
def get_stats():
    """Get global statistics."""
    return db.get_global_stats()


@app.get("/api/sprints")
def list_sprints(limit: int = 20):
    """Get recent sprints from DB."""
    return {
        "recent": db.get_recent_sprints(limit),
        "total": db.get_total_sprints()
    }


@app.get("/api/sprints/{sprint_id}")
def get_sprint_detail(sprint_id: str):
    """Get sprint details from DB."""
    sprint = db.get_sprint(sprint_id)
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint not found")
    return sprint

@app.get("/api/live")
def get_live_state():
    """Live progress for the currently running sprint/break/session.
    Frontend polls this every ~1s while a sprint is running."""
    return live.snapshot()


@app.post("/api/db/reset")
def reset_database_endpoint():
    """DANGER: Reset all data."""
    db.reset_database()
    for s in emotional_state:
        emotional_state[s] = {"frustration": 0, "happiness": 5}
    return {"status": "Database reset"}


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
    
    # NEW: persist
    db.record_emotion(req.student_name, state["frustration"], state["happiness"], context="Manual update")
    # NEW IN V3: broadcast
    ws.manager.broadcast_sync(ws.event_emotion_updated(
        req.student_name, state["frustration"], state["happiness"], "Manual update"
    ))
    
    return {"student_name": req.student_name, "state": state}


@app.post("/api/emotions/reset")
def reset_emotions():
    """Reseteaza emotiile inainte de o noua sesiune."""
    for s in emotional_state:
        emotional_state[s] = {"frustration": 0, "happiness": 5}
        db.record_emotion(s, 0, 5, context="Reset")
        # NEW IN V3: broadcast
        ws.manager.broadcast_sync(ws.event_emotion_updated(s, 0, 5, "Reset"))
    return emotional_state


# =============================================================================
# HEALTH CHECK
# =============================================================================

@app.get("/")
def root():
    stats = db.get_global_stats()
    return {
        "status": "running",
        "version": "3.0",
        "config": {k: v for k, v in classroom_config.items() if k != "current_lesson"},
        "current_lesson_loaded": classroom_config.get("current_lesson") is not None,
        "students_emotions": emotional_state,
        "global_stats": stats,
        "websocket_connections": len(ws.manager.active_connections),  # NEW IN V3
        "endpoints": {
            "websocket": "ws://localhost:8000/ws",  # NEW IN V3
            "full_session": "POST /api/session/run",
            "sprint_only": "POST /api/sprint/run",
            "break_only": "POST /api/break/run",
            "leaderboard": "GET /api/leaderboard",
            "achievements": "GET /api/achievements",
            "stats": "GET /api/stats",
            "docs": "/docs"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
