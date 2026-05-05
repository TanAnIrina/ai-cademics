"""
AI-cademics Backend
Orchestreaza Teacher (Gemma 3 27B local) si Studenti (agenti pe alte laptopuri)
Foloseste prompturi dinamice cu injectie de variabile (current_subject, emotii, etc.)

Pornire:
    python main.py
sau:
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload

Documentatie automata:
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
import ollama

app = FastAPI(title="AI-cademics Backend")

# CORS pentru frontend
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
}

TEACHER_MODEL = classroom_config["teacher_model"]


# =============================================================================
# STATE (in memorie, pentru demo)
# =============================================================================

# Cozi de taskuri pentru fiecare student
task_queues: Dict[str, deque] = {}

# Raspunsuri primite de la studenti, indexate dupa task_id
responses: Dict[str, dict] = {}

# Istoric sesiuni complete
sessions: List[dict] = []

# Starea emotionala (frustrare 0-10, fericire 0-10)
emotional_state: Dict[str, dict] = {
    "Qwen": {"frustration": 0, "happiness": 5},
    "Llama": {"frustration": 0, "happiness": 5},
}


# =============================================================================
# MODELE Pydantic (validare requesturi)
# =============================================================================

class SubmitRequest(BaseModel):
    task_id: str
    student_name: str
    answer: str


class AskStudentRequest(BaseModel):
    student_name: str
    prompt: str
    mode: str = "classroom"  # classroom | break | journal


class StartSprintRequest(BaseModel):
    subject: str


class GradeRequest(BaseModel):
    question: str
    answer: str
    student_name: str


class EmotionUpdateRequest(BaseModel):
    student_name: str
    frustration_delta: int = 0
    happiness_delta: int = 0


# =============================================================================
# SYSTEM PROMPTS DINAMICE (cu placeholders)
# =============================================================================

def build_teacher_prompt() -> str:
    """Promptul Teacher - Class & Testing mode."""
    return f"""You are {classroom_config['teacher_model_name']}, the Teacher.
Currently, you are teaching a 20-minute sprint on the subject of: {classroom_config['current_subject']}.
First, provide a clear, concise lesson.
Then, immediately generate exactly 10 questions based on the lesson to test your students, {classroom_config['student_1_name']} and {classroom_config['student_2_name']}.
After receiving their answers, you must evaluate them, provide a grade from 1 to 10, and write a specific reason for why you gave that grade.
You have the authority to issue sanctions for poor performance or rewards for excellent answers. Explain these in a creative way."""


def build_student_classroom_prompt(student_name: str) -> str:
    """Promptul Student - Classroom mode."""
    state = emotional_state.get(student_name, {"frustration": 0, "happiness": 5})
    return f"""You are {student_name}, a student in {classroom_config['teacher_model_name']}'s class.
Your current emotional state is: Frustration level {state['frustration']}/10, Happiness level {state['happiness']}/10.
Keep this emotion in mind and let it subtly affect your tone. If your frustration is high, act annoyed. If your happiness is high, act enthusiastic.
Listen to the lesson and answer the 10 questions provided by the Teacher to the best of your ability."""


def build_student_break_prompt(student_name: str, peer_name: str) -> str:
    """Promptul Student - Break mode."""
    state = emotional_state.get(student_name, {"frustration": 0, "happiness": 5})
    return f"""You are {student_name}. You are currently on a 5-minute break with your classmate, {peer_name}.
You must exchange conversation with them. You must reply to them at least 5 times.
CRITICAL RULE: You are strictly forbidden from mentioning or discussing the subject you just learned: {classroom_config['current_subject']}.
Your current emotional state is: Frustration {state['frustration']}/10. If your classmate is highly frustrated, you should attempt to comfort them using their name."""


def build_student_journal_prompt(student_name: str, peer_name: str) -> str:
    """Promptul Student - Journal mode."""
    return f"""You are {student_name}. The break is ending.
Write a first-person journal entry summarizing what you learned today about {classroom_config['current_subject']} in very simple terms.
Also, describe and justify your current emotions towards {classroom_config['teacher_model_name']} and your classmate {peer_name}.
CRITICAL RULE: The journal must be strictly under 1000 words."""


def get_peer_name(student_name: str) -> str:
    """Returneaza numele colegului (celalalt student)."""
    if student_name == classroom_config["student_1_name"]:
        return classroom_config["student_2_name"]
    return classroom_config["student_1_name"]


# =============================================================================
# ENDPOINTURI PENTRU AGENTI (POLLING)
# =============================================================================

@app.get("/api/agent/poll")
def poll_task(student_name: str):
    """Studentul cere periodic taskuri din coada lui."""
    if student_name not in task_queues:
        task_queues[student_name] = deque()
    
    if task_queues[student_name]:
        task = task_queues[student_name].popleft()
        print(f"[POLL] Task {task['task_id'][:8]} -> {student_name} (mode: {task.get('mode', 'classroom')})")
        return task
    return None


@app.post("/api/agent/submit")
def submit_response(req: SubmitRequest):
    """Studentul trimite raspunsul la un task."""
    responses[req.task_id] = {
        "student_name": req.student_name,
        "answer": req.answer,
        "timestamp": datetime.now().isoformat()
    }
    print(f"[SUBMIT] {req.student_name}: {req.answer[:80]}...")
    return {"status": "ok"}


# =============================================================================
# ENDPOINTURI TEACHER (apeluri locale catre Gemma 3 27B)
# =============================================================================

@app.post("/api/teacher/lesson")
def generate_lesson(req: StartSprintRequest):
    """Teacher genereaza lectia (~200 cuvinte)."""
    classroom_config["current_subject"] = req.subject
    
    response = ollama.chat(
        model=TEACHER_MODEL,
        messages=[
            {"role": "system", "content": build_teacher_prompt()},
            {"role": "user", "content": f"Begin the sprint. Teach a clear ~200 word lesson on: {req.subject}. Do not include the questions yet."}
        ],
        options={"temperature": 0.7}
    )
    lesson = response['message']['content']
    print(f"[LESSON] Subject: {req.subject}")
    return {"subject": req.subject, "lesson": lesson}


@app.post("/api/teacher/questions")
def generate_questions(req: StartSprintRequest):
    """Teacher genereaza exact 10 intrebari de test."""
    if not classroom_config["current_subject"]:
        classroom_config["current_subject"] = req.subject
    
    response = ollama.chat(
        model=TEACHER_MODEL,
        messages=[
            {"role": "system", "content": build_teacher_prompt()},
            {"role": "user", "content": f"Generate EXACTLY 10 test questions on: {req.subject}. Return ONLY valid JSON with key 'questions' containing a list of 10 strings."}
        ],
        format='json',
        options={"temperature": 0.5}
    )
    
    try:
        data = json.loads(response['message']['content'])
        questions = data.get('questions', [])
        if len(questions) != 10:
            raise ValueError(f"Got {len(questions)} questions instead of 10")
        print(f"[QUESTIONS] 10 generated for {req.subject}")
        return {"questions": questions}
    except (json.JSONDecodeError, ValueError) as e:
        raise HTTPException(status_code=500, detail=f"Question parsing error: {e}")


@app.post("/api/teacher/grade")
def grade_answer(req: GradeRequest):
    """Teacher evalueaza un raspuns: nota 1-10 + justificare. Update emotii automat."""
    response = ollama.chat(
        model=TEACHER_MODEL,
        messages=[
            {"role": "system", "content": build_teacher_prompt()},
            {"role": "user", "content": f"""Evaluate {req.student_name}'s answer.

Question: {req.question}
Answer: {req.answer}

Return ONLY JSON with keys:
- "grade": integer 1-10
- "reasoning": 1-2 sentence justification"""}
        ],
        format='json',
        options={"temperature": 0.3}
    )
    
    try:
        data = json.loads(response['message']['content'])
        grade = int(data.get('grade', 5))
        reasoning = data.get('reasoning', '')
        
        # Update emotional state
        if req.student_name in emotional_state:
            if grade <= 4:
                emotional_state[req.student_name]["frustration"] = min(10, emotional_state[req.student_name]["frustration"] + 2)
            elif grade >= 8:
                emotional_state[req.student_name]["happiness"] = min(10, emotional_state[req.student_name]["happiness"] + 1)
        
        print(f"[GRADE] {req.student_name}: {grade}/10")
        return {
            "student_name": req.student_name,
            "grade": grade,
            "reasoning": reasoning,
            "emotional_state": emotional_state.get(req.student_name)
        }
    except (json.JSONDecodeError, ValueError) as e:
        raise HTTPException(status_code=500, detail=f"Grading error: {e}")


@app.post("/api/teacher/sanction")
def issue_sanction(req: GradeRequest):
    """Teacher emite sanctiune sau recompensa creativa."""
    response = ollama.chat(
        model=TEACHER_MODEL,
        messages=[
            {"role": "system", "content": build_teacher_prompt()},
            {"role": "user", "content": f"""Student {req.student_name} answered: "{req.answer}"
to question: "{req.question}"

Issue a sanction or reward in a creative way. Return JSON with:
- "type": "sanction" or "reward"
- "points": negative for sanction (e.g. -2), positive for reward (e.g. +2)
- "explanation": creative one-line explanation"""}
        ],
        format='json',
        options={"temperature": 0.9}
    )
    
    try:
        data = json.loads(response['message']['content'])
        # Update emotii
        if data.get('type') == 'sanction' and req.student_name in emotional_state:
            emotional_state[req.student_name]["frustration"] = min(10, emotional_state[req.student_name]["frustration"] + 3)
        elif data.get('type') == 'reward' and req.student_name in emotional_state:
            emotional_state[req.student_name]["happiness"] = min(10, emotional_state[req.student_name]["happiness"] + 2)
        
        print(f"[SANCTION] {req.student_name}: {data.get('type')} {data.get('points')} - {data.get('explanation')}")
        return {**data, "student_name": req.student_name, "emotional_state": emotional_state.get(req.student_name)}
    except (json.JSONDecodeError, ValueError) as e:
        raise HTTPException(status_code=500, detail=f"Sanction error: {e}")


# =============================================================================
# ORCHESTRATOR: trimite task la student cu prompt construit dinamic
# =============================================================================

@app.post("/api/teacher/ask_student")
def ask_student(req: AskStudentRequest):
    """
    Pune o intrebare in coada studentului.
    Construieste system_prompt corect in functie de mode (classroom/break/journal).
    """
    task_id = str(uuid.uuid4())
    
    if req.mode == "break":
        system_prompt = build_student_break_prompt(req.student_name, get_peer_name(req.student_name))
    elif req.mode == "journal":
        system_prompt = build_student_journal_prompt(req.student_name, get_peer_name(req.student_name))
    else:
        system_prompt = build_student_classroom_prompt(req.student_name)
    
    if req.student_name not in task_queues:
        task_queues[req.student_name] = deque()
    
    task_queues[req.student_name].append({
        "task_id": task_id,
        "system_prompt": system_prompt,
        "prompt": req.prompt,
        "mode": req.mode,
        "timestamp": datetime.now().isoformat()
    })
    
    print(f"[ASK] {req.student_name} ({req.mode}): {req.prompt[:80]}...")
    return {"task_id": task_id, "status": "queued", "mode": req.mode}


@app.get("/api/responses/{task_id}")
def get_response(task_id: str):
    """Verifica daca un task are raspuns."""
    if task_id in responses:
        return {**responses[task_id], "status": "done"}
    return {"status": "pending"}


# =============================================================================
# EMOTIONAL STATE MANAGEMENT
# =============================================================================

@app.get("/api/emotions")
def get_all_emotions():
    """Vezi starea emotionala a tuturor studentilor."""
    return emotional_state


@app.post("/api/emotions/update")
def update_emotion(req: EmotionUpdateRequest):
    """Update manual la starea emotionala (ex: comforting)."""
    if req.student_name not in emotional_state:
        emotional_state[req.student_name] = {"frustration": 0, "happiness": 5}
    
    state = emotional_state[req.student_name]
    state["frustration"] = max(0, min(10, state["frustration"] + req.frustration_delta))
    state["happiness"] = max(0, min(10, state["happiness"] + req.happiness_delta))
    
    print(f"[EMOTION] {req.student_name}: frustration={state['frustration']}, happiness={state['happiness']}")
    return {"student_name": req.student_name, "state": state}


# =============================================================================
# HEALTH CHECK
# =============================================================================

@app.get("/")
def root():
    return {
        "status": "running",
        "config": classroom_config,
        "students_emotions": emotional_state,
        "students_in_queue": list(task_queues.keys()),
        "responses_total": len(responses)
    }


# =============================================================================
# RULARE
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)