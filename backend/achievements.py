"""
Achievement/Badge system for AI-cademics.
Detects accomplishments and unlocks badges for students.
"""

from typing import Dict, List, Optional
import database as db


# =============================================================================
# ACHIEVEMENT DEFINITIONS
# =============================================================================

ACHIEVEMENTS = {
    "first_perfect_score": {
        "key": "first_perfect_score",
        "title": "First Perfect Score 🌟",
        "description": "Got your first 10/10",
        "icon": "🌟",
        "rarity": "uncommon"
    },
    "comeback_kid": {
        "key": "comeback_kid",
        "title": "Comeback Kid 💪",
        "description": "Recovered from 3 consecutive bad grades (≤4) with a great answer (≥8)",
        "icon": "💪",
        "rarity": "rare"
    },
    "best_friend": {
        "key": "best_friend",
        "title": "Best Friend 🤗",
        "description": "Comforted your peer 5 times",
        "icon": "🤗",
        "rarity": "rare"
    },
    "academic_warrior": {
        "key": "academic_warrior",
        "title": "Academic Warrior 🎓",
        "description": "Completed 10 sprints",
        "icon": "🎓",
        "rarity": "epic"
    },
    "straight_a_student": {
        "key": "straight_a_student",
        "title": "Straight A Student ✨",
        "description": "Got 10/10 on every question in a single sprint",
        "icon": "✨",
        "rarity": "legendary"
    },
    "social_butterfly": {
        "key": "social_butterfly",
        "title": "Social Butterfly 🦋",
        "description": "Mentioned your peer's name 10+ times across breaks",
        "icon": "🦋",
        "rarity": "common"
    },
    "iron_will": {
        "key": "iron_will",
        "title": "Iron Will 🛡️",
        "description": "Kept frustration ≤3 throughout an entire sprint",
        "icon": "🛡️",
        "rarity": "rare"
    },
    "ate_and_left_no_crumbs": {
        "key": "ate_and_left_no_crumbs",
        "title": "Ate and Left No Crumbs 💅",
        "description": "Got a 10/10 on the first question of a sprint",
        "icon": "💅",
        "rarity": "uncommon"
    },
    "no_cap_violator": {
        "key": "no_cap_violator",
        "title": "No Cap Violator 🚫",
        "description": "Got penalized for using slang in classroom 3 times",
        "icon": "🚫",
        "rarity": "common"
    },
    "peace_maker": {
        "key": "peace_maker",
        "title": "Peace Maker 🕊️",
        "description": "Reduced peer's frustration through comforting 5+ times",
        "icon": "🕊️",
        "rarity": "epic"
    },
    "total_recall": {
        "key": "total_recall",
        "title": "Total Recall 🧠",
        "description": "Got 90%+ average on a sprint",
        "icon": "🧠",
        "rarity": "uncommon"
    },
    "rookie_no_more": {
        "key": "rookie_no_more",
        "title": "Rookie No More 📚",
        "description": "Completed first sprint",
        "icon": "📚",
        "rarity": "common"
    },
    "subject_master": {
        "key": "subject_master",
        "title": "Subject Master 👑",
        "description": "Got 9+ average on the same subject 3 times",
        "icon": "👑",
        "rarity": "legendary"
    },
    "trolled_by_teacher": {
        "key": "trolled_by_teacher",
        "title": "Trolled by Teacher 😅",
        "description": "Received 5 sanctions in one sprint",
        "icon": "😅",
        "rarity": "rare"
    },
    "teacher_pet": {
        "key": "teacher_pet",
        "title": "Teacher's Pet 🍎",
        "description": "Earned 5 rewards in a single sprint",
        "icon": "🍎",
        "rarity": "epic"
    },
}

RARITY_COLORS = {
    "common": "#9CA3AF",
    "uncommon": "#10B981",
    "rare": "#3B82F6",
    "epic": "#8B5CF6",
    "legendary": "#F59E0B"
}


# =============================================================================
# DETECTION LOGIC
# =============================================================================

def check_sprint_achievements(student_name: str, sprint_data: Dict) -> List[Dict]:
    """
    Check all sprint-related achievements after a sprint completes.
    Returns list of newly unlocked achievements.
    """
    sprint_id = sprint_data.get("sprint_id")
    answers = sprint_data.get("answers", {}).get(student_name, [])
    
    if not answers:
        return []
    
    newly_unlocked = []
    
    grades = [a.get("grade") for a in answers if a.get("grade") is not None]
    if not grades:
        return []
    
    avg_grade = sum(grades) / len(grades)
    perfect_count = sum(1 for g in grades if g == 10)
    
    # ----- First Perfect Score -----
    if perfect_count > 0:
        if _try_unlock(student_name, "first_perfect_score", sprint_id, newly_unlocked):
            pass
    
    # ----- Ate and Left No Crumbs (10/10 on first question) -----
    if grades[0] == 10:
        _try_unlock(student_name, "ate_and_left_no_crumbs", sprint_id, newly_unlocked)
    
    # ----- Straight A Student (all 10/10) -----
    if all(g == 10 for g in grades) and len(grades) == 10:
        _try_unlock(student_name, "straight_a_student", sprint_id, newly_unlocked)
    
    # ----- Total Recall (90%+ avg) -----
    if avg_grade >= 9.0:
        _try_unlock(student_name, "total_recall", sprint_id, newly_unlocked)
    
    # ----- Comeback Kid (recovered from 3 bad grades) -----
    if len(grades) >= 4:
        for i in range(3, len(grades)):
            if all(g <= 4 for g in grades[i-3:i]) and grades[i] >= 8:
                _try_unlock(student_name, "comeback_kid", sprint_id, newly_unlocked)
                break
    
    # ----- Trolled by Teacher (5 sanctions in sprint) -----
    sanctions = sum(1 for a in answers if a.get("action") and a["action"].get("type") == "sanction")
    if sanctions >= 5:
        _try_unlock(student_name, "trolled_by_teacher", sprint_id, newly_unlocked)
    
    # ----- Teacher's Pet (5 rewards in sprint) -----
    rewards = sum(1 for a in answers if a.get("action") and a["action"].get("type") == "reward")
    if rewards >= 5:
        _try_unlock(student_name, "teacher_pet", sprint_id, newly_unlocked)
    
    # ----- Iron Will (low frustration throughout) -----
    final_state = sprint_data.get("summary", {}).get(student_name, {}).get("final_emotional_state", {})
    if final_state and final_state.get("frustration", 10) <= 3 and avg_grade < 7:
        # Low frustration despite low grades = iron will
        _try_unlock(student_name, "iron_will", sprint_id, newly_unlocked)
    
    return newly_unlocked


def check_cumulative_achievements(student_name: str, sprint_id: Optional[str] = None) -> List[Dict]:
    """
    Check achievements based on cumulative student stats.
    Called after each sprint to detect long-term achievements.
    """
    student = db.get_student(student_name)
    if not student:
        return []
    
    newly_unlocked = []
    
    # ----- Rookie No More (first sprint) -----
    if student["total_sprints"] >= 1:
        _try_unlock(student_name, "rookie_no_more", sprint_id, newly_unlocked)
    
    # ----- Academic Warrior (10 sprints) -----
    if student["total_sprints"] >= 10:
        _try_unlock(student_name, "academic_warrior", sprint_id, newly_unlocked)
    
    # ----- Best Friend (5 comforts) -----
    if student["total_comforts_given"] >= 5:
        _try_unlock(student_name, "best_friend", sprint_id, newly_unlocked)
    
    # ----- Peace Maker (5+ comforts in total) -----
    if student["total_comforts_given"] >= 5:
        _try_unlock(student_name, "peace_maker", sprint_id, newly_unlocked)
    
    # ----- No Cap Violator (3 slang penalties) -----
    if student["total_slang_penalties"] >= 3:
        _try_unlock(student_name, "no_cap_violator", sprint_id, newly_unlocked)
    
    # ----- Subject Master -----
    # This requires more complex query: 3 sprints on same subject with avg ≥9
    if _check_subject_master(student_name):
        _try_unlock(student_name, "subject_master", sprint_id, newly_unlocked)
    
    return newly_unlocked


def check_break_achievements(student_name: str, break_data: Dict, peer_name: str) -> List[Dict]:
    """Check achievements after a break completes."""
    newly_unlocked = []
    break_id = break_data.get("break_id")
    
    # Count peer mentions across all student's messages in this break
    mentions = 0
    for msg in break_data.get("conversation", []):
        if msg.get("speaker") == student_name:
            if peer_name.lower() in msg.get("message", "").lower():
                mentions += 1
    
    # Cumulative check across all breaks
    student = db.get_student(student_name)
    if student:
        # Social Butterfly = 10+ total peer mentions (we'd need more tracking, simplified)
        # For now, just unlock if 3+ in single break (simpler heuristic)
        if mentions >= 3:
            _try_unlock(student_name, "social_butterfly", break_id, newly_unlocked)
    
    return newly_unlocked


def _check_subject_master(student_name: str) -> bool:
    """Check if student has 3+ sprints on same subject with avg >= 9."""
    progression = db.get_student_progression(student_name)
    if not progression:
        return False
    
    subject_counts = {}
    for entry in progression:
        if entry["average_grade"] and entry["average_grade"] >= 9:
            subject = entry["subject"]
            subject_counts[subject] = subject_counts.get(subject, 0) + 1
    
    return any(count >= 3 for count in subject_counts.values())


def _try_unlock(student_name: str, achievement_key: str, sprint_id: Optional[str], 
                 newly_unlocked: List[Dict]):
    """Attempt to unlock achievement and add to newly_unlocked if first time."""
    if achievement_key not in ACHIEVEMENTS:
        return
    
    if db.unlock_achievement(student_name, achievement_key, sprint_id):
        achievement_def = ACHIEVEMENTS[achievement_key].copy()
        achievement_def["student_name"] = student_name
        achievement_def["color"] = RARITY_COLORS.get(achievement_def["rarity"], "#9CA3AF")
        newly_unlocked.append(achievement_def)


# =============================================================================
# QUERY API
# =============================================================================

def get_student_badges(student_name: str) -> List[Dict]:
    """Get all unlocked achievements for student with full info."""
    unlocked = db.get_student_achievements(student_name)
    
    result = []
    for a in unlocked:
        if a["achievement_key"] in ACHIEVEMENTS:
            badge = ACHIEVEMENTS[a["achievement_key"]].copy()
            badge["unlocked_at"] = a["unlocked_at"]
            badge["sprint_id"] = a.get("sprint_id")
            badge["color"] = RARITY_COLORS.get(badge["rarity"], "#9CA3AF")
            result.append(badge)
    
    return result


def get_all_achievements() -> List[Dict]:
    """Get all available achievements (for showing locked ones in UI)."""
    return [
        {**a, "color": RARITY_COLORS.get(a["rarity"], "#9CA3AF")}
        for a in ACHIEVEMENTS.values()
    ]


def get_locked_achievements(student_name: str) -> List[Dict]:
    """Get achievements not yet unlocked by student."""
    unlocked_keys = {a["achievement_key"] for a in db.get_student_achievements(student_name)}
    return [
        {**a, "color": RARITY_COLORS.get(a["rarity"], "#9CA3AF")}
        for key, a in ACHIEVEMENTS.items()
        if key not in unlocked_keys
    ]
