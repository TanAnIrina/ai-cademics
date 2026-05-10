"""
WebSocket connection manager + LLM streaming utilities.
Real-time event broadcasting for AI-cademics dashboard.
"""

from fastapi import WebSocket
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio
import json


# =============================================================================
# WEBSOCKET CONNECTION MANAGER
# =============================================================================

class ConnectionManager:
    """Manages active WebSocket connections and broadcasts events."""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.event_history: List[Dict] = []  # last 100 events
        self.MAX_HISTORY = 100
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        # Send recent history to new connection
        for event in self.event_history[-20:]:
            try:
                await websocket.send_json(event)
            except Exception:
                pass
        print(f"[WS] Client connected. Total: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        print(f"[WS] Client disconnected. Total: {len(self.active_connections)}")
    
    async def broadcast(self, event: Dict[str, Any]):
        """Broadcast event to all connected clients."""
        # Add timestamp if missing
        if "timestamp" not in event:
            event["timestamp"] = datetime.now().isoformat()
        
        # Save to history
        self.event_history.append(event)
        if len(self.event_history) > self.MAX_HISTORY:
            self.event_history = self.event_history[-self.MAX_HISTORY:]
        
        # Broadcast to all clients
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(event)
            except Exception:
                disconnected.append(connection)
        
        for conn in disconnected:
            self.disconnect(conn)
    
    def broadcast_sync(self, event: Dict[str, Any]):
        """Sync version for use in sync contexts. Schedules broadcast on event loop."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self.broadcast(event))
            else:
                loop.run_until_complete(self.broadcast(event))
        except RuntimeError:
            # No event loop, store in history only
            event["timestamp"] = datetime.now().isoformat()
            self.event_history.append(event)


# Singleton instance
manager = ConnectionManager()


# =============================================================================
# EVENT TYPE HELPERS - structured event creation
# =============================================================================

def event_lesson_streaming(content: str, sprint_id: str) -> Dict:
    return {
        "type": "lesson_streaming",
        "sprint_id": sprint_id,
        "content": content
    }


def event_lesson_complete(lesson: str, sprint_id: str, subject: str) -> Dict:
    return {
        "type": "lesson_complete",
        "sprint_id": sprint_id,
        "subject": subject,
        "lesson": lesson
    }


def event_questions_generated(questions: List[str], sprint_id: str) -> Dict:
    return {
        "type": "questions_generated",
        "sprint_id": sprint_id,
        "questions": questions,
        "count": len(questions)
    }


def event_student_thinking(student: str, question_idx: int, question: str) -> Dict:
    return {
        "type": "student_thinking",
        "student": student,
        "question_idx": question_idx,
        "question": question
    }


def event_answer_received(student: str, question_idx: int, answer: str) -> Dict:
    return {
        "type": "answer_received",
        "student": student,
        "question_idx": question_idx,
        "answer": answer
    }


def event_grade_assigned(student: str, question_idx: int, grade: int, reasoning: str) -> Dict:
    return {
        "type": "grade_assigned",
        "student": student,
        "question_idx": question_idx,
        "grade": grade,
        "reasoning": reasoning
    }


def event_action_issued(student: str, action_type: str, points: int, explanation: str) -> Dict:
    return {
        "type": "action_issued",
        "student": student,
        "action_type": action_type,
        "points": points,
        "explanation": explanation
    }


def event_emotion_updated(student: str, frustration: int, happiness: int, reason: str = "") -> Dict:
    return {
        "type": "emotion_updated",
        "student": student,
        "frustration": frustration,
        "happiness": happiness,
        "reason": reason
    }


def event_achievement_unlocked(student: str, achievement: Dict) -> Dict:
    return {
        "type": "achievement_unlocked",
        "student": student,
        "achievement": achievement
    }


def event_break_message(speaker: str, message: str, round_num: int, 
                          mentioned_subject: bool = False, comforted: bool = False) -> Dict:
    return {
        "type": "break_message",
        "speaker": speaker,
        "message": message,
        "round": round_num,
        "mentioned_subject": mentioned_subject,
        "comforted_peer": comforted
    }


def event_sprint_started(sprint_id: str, subject: str) -> Dict:
    return {
        "type": "sprint_started",
        "sprint_id": sprint_id,
        "subject": subject
    }


def event_sprint_completed(sprint_id: str, summary: Dict) -> Dict:
    return {
        "type": "sprint_completed",
        "sprint_id": sprint_id,
        "summary": summary
    }


def event_break_started(break_id: str, sprint_id: Optional[str] = None) -> Dict:
    return {
        "type": "break_started",
        "break_id": break_id,
        "sprint_id": sprint_id
    }


def event_break_completed(break_id: str, summary: Dict) -> Dict:
    return {
        "type": "break_completed",
        "break_id": break_id,
        "summary": summary
    }


def event_session_started(session_id: str, subject: str) -> Dict:
    return {
        "type": "session_started",
        "session_id": session_id,
        "subject": subject
    }


def event_session_completed(session_id: str, duration: float) -> Dict:
    return {
        "type": "session_completed",
        "session_id": session_id,
        "duration_seconds": duration
    }


# =============================================================================
# OLLAMA STREAMING UTILITY
# =============================================================================

def stream_ollama_chat(model: str, messages: List[Dict], 
                       sprint_id: Optional[str] = None,
                       event_type: str = "lesson_streaming",
                       options: Optional[Dict] = None) -> str:
    """
    Stream from Ollama and broadcast each chunk via WebSocket.
    Returns the full accumulated response.
    """
    import ollama
    
    if options is None:
        options = {"temperature": 0.7}
    
    full_response = ""
    
    try:
        stream = ollama.chat(
            model=model,
            messages=messages,
            stream=True,
            options=options
        )
        
        for chunk in stream:
            content = chunk.get("message", {}).get("content", "")
            if content:
                full_response += content
                # Broadcast incremental update
                manager.broadcast_sync({
                    "type": event_type,
                    "sprint_id": sprint_id,
                    "content": content,           # this chunk
                    "accumulated": full_response,  # full text so far
                    "is_final": False
                })
        
        # Final event
        manager.broadcast_sync({
            "type": event_type,
            "sprint_id": sprint_id,
            "content": "",
            "accumulated": full_response,
            "is_final": True
        })
        
    except Exception as e:
        manager.broadcast_sync({
            "type": "error",
            "context": event_type,
            "error": str(e)
        })
        raise
    
    return full_response
