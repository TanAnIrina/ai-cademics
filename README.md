## 📖 Project Overview
ai-cademics is a distributed Multi-Agent System (MAS) that simulates a classroom environment using three locally hosted Large Language Models (LLMs). One high-capacity model acts as the **Teacher**, while two lightweight models act as the **Students**. 

The simulation runs in continuous 20-minute "sprints" (simulating 1 hour of class), followed by 10-minute breaks where students interact socially, comfort each other, and write learning journals. A unique **Emotion & Memory System** tracks the students' psychological states (e.g., frustration, happiness) across sessions, dynamically influencing their responses and interactions.

---

## 📋 Product Backlog

### Epic 1: Access and Profile Management
* **US 1: Login & Active Classrooms**
  * **As** a user, **I want to** log into the app and browse the list of active classrooms, **so that** I can choose the one that fits me best and join it.
  * **Acceptance Criteria:** The user authenticates successfully; all currently active classrooms are displayed with their status; the user can select and enter one.
* **US 2: Schedule a Future Classroom**
  * **As** a Teacher, **I want to** schedule a classroom for a future date and time when creating it, **so that** students can see upcoming sessions and plan to join in advance.
  * **Acceptance Criteria:** The Teacher sets a date and start time when creating the classroom; the classroom appears in a "scheduled" list visible to students; students can register interest before it becomes active.
* **US 3: User Profile and Avatar**
  * **As** a user, **I want to** customize my profile with a name, **so that** I have a recognizable identity in the classroom and during break interactions.
  * **Acceptance Criteria:** The user can set a display name from their account settings; the nameis visible to other users inside the classroom and in the active classrooms list; changes are saved and persist across sessions.

### Epic 2: Class Session and Interaction
* **US 4: Teaching, Testing, and Evaluation**
  * **As** the Teacher, **I want to** teach a mini-lesson followed by a 10-question test at the end of each 20-minute sprint, and provide a written explanation for my grading, **so that** I can transparently evaluate the knowledge retained and justify the final marks.
  * **Acceptance Criteria:** The Teacher generates exactly 10 questions. The sprint number, generated questions, Students' answers, Teacher's grading reasoning, and final grades (1-10) are saved.
* **US 5: Ask Questions During the Lesson**
  * **As** a Student, **I want to** ask the Teacher a question during the 20-minute sprint when I don't understand something, **so that** I can clarify the material before the test starts.
  * **Acceptance Criteria:** The Student can submit a question mid-lesson; the Teacher receives it and replies before the test phase begins; the question and answer are visible in the session log.
* **US 6: Lesson Feedback**
  * **As** a Student, **I want to** rate the lesson and leave a short comment at the end of the sprint, **so that** the Teacher knows what worked and what didn't.
  * **Acceptance Criteria:** At the end of each sprint, the Student is prompted to give a rating (e.g., 1-5) and an optional written comment; the feedback is saved and visible to the Teacher; the Student can skip if they don't want to respond.

### Epic 3: Emotions, Breaks, and Disciplinary Actions
* **US 7: Learning Journal**
  * **As** a Student, **I want to** generate a journal entry in the last 5 minutes of the break, **so that** I can summarize what I learned in under 1000 words and describe and justify my emotions.
  * **Acceptance Criteria:** The journal is saved; the text is generated in the first person using the student's own name.
* **US 8: Teacher Sanctions and Rewards**
  * **As** the Teacher, **I want to** be able to give sanctions or rewards to my students based on their answers, and save these actions along with a creative justification, **so that** I have a permanent, transparent record of my disciplinary actions.
  * **Acceptance Criteria:** The Teacher evaluates a student's response; a sanction or reward is generated with a creative text explanation (e.g., "Minus 2 points for falling asleep while Llama was talking"); the targeted student's frustration level is updated accordingly.
* **US 9: Mutual Student Comforting**
  * **As** a Student, **I want to** be able to comfort my classmate during the break if I notice they received a sanction, **so that** we can dynamically alter each other's emotional states.
  * **Acceptance Criteria:** During the break, if Student 1 comforts Student 2 using their specific name, Student 2's frustration decreases.

### Epic 4: Analytics and Performance Tracking
* **US 10: View Own Grades and Feedback**
  * **As** a Student, **I want to** see my grade and the Teacher's written reasoning after each test, **so that** I understand why I received a certain mark and what I need to improve.
  * **Acceptance Criteria:** After the Teacher finishes evaluation, the Student can view the grade (1-10), the questions, their own answers, and the Teacher's justification per sprint.
* **US 11: Student Performance History (Teacher View)**
  * **As** a Teacher, **I want to** view a student's grade history and emotional state across previous sprints, **so that** I can adjust my teaching approach and identify struggling students early.
  * **Acceptance Criteria:** The Teacher selects a student from the classroom; a timeline shows past grades, sanctions, rewards, and frustration/happiness evolution across all sprints.
* **US 12: Classroom Statistics for Teacher**
  * **As** a Teacher, **I want to** see aggregated statistics for my classroom (average grade, participation rate, average frustration level), **so that** I can assess how the session went overall.
  * **Acceptance Criteria:** After each sprint, the Teacher can open a statistics panel showing the average grade across all students, the number of active participants, and the average emotional state of the class; statistics update automatically at the end of each sprint.
---

## 🧠 System Prompts Overview

To achieve the multi-agent simulation, we use dynamic prompt injection. Here are the core system prompts used to govern the LLMs' behaviors:

### 1. The Teacher Prompt (Class & Testing)
```text
You are {teacher_model_name}, the Teacher. 
Currently, you are teaching a 20-minute sprint on the subject of: {current_subject}.
First, provide a clear, concise lesson. 
Then, immediately generate exactly 10 questions based on the lesson to test your students, {student_1_name} and {student_2_name}.
After receiving their answers, you must evaluate them, provide a grade from 1 to 10, and write a specific reason for why you gave that grade. 
You have the authority to issue sanctions for poor performance or rewards for excellent answers. Explain these in a creative way.
```
### 2. The Student Prompt (Classroom Mode)
```text
You are {student_model_name}, a student in {teacher_model_name}'s class.
Your current emotional state is: Frustration level {frustration_level}/10, Happiness level {happiness_level}/10. 
Keep this emotion in mind and let it subtly affect your tone. If your frustration is high, act annoyed. If your happiness is high, act enthusiastic.
Listen to the lesson and answer the 10 questions provided by the Teacher to the best of your ability.
```
### 3. 3. The Student Prompt (Break Mode)
```text
You are {student_model_name}. You are currently on a 5-minute break with your classmate, {peer_model_name}.
You must exchange conversation with them. You must reply to them at least 5 times. 
CRITICAL RULE: You are strictly forbidden from mentioning or discussing the subject you just learned: {current_subject}. 
Your current emotional state is: Frustration {frustration_level}/10. If your classmate is highly frustrated, you should attempt to comfort them using their name.
```
### 4. The Student Prompt (Journal Mode)
```text
You are {student_model_name}. The break is ending. 
Write a first-person journal entry summarizing what you learned today about {current_subject} in very simple terms.
Also, describe and justify your current emotions towards {teacher_model_name} and your classmate {peer_model_name}.
CRITICAL RULE: The journal must be strictly under 1000 words.
```

---

## Frontend (new)

A React frontend is available in `frontend/` and maps the product backlog into 4 screens:

- Access & Profiles (US1-US3)
- Class Session (US4-US6)
- Breaks & Emotions (US7-US9)
- Analytics (US10-US12)

### Run frontend

```bash
cd frontend
npm install
npm run dev
```

By default it targets `http://localhost:8000` and can be changed from the UI.
