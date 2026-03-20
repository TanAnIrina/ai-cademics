## 📖 Project Overview
ai-cademics is a distributed Multi-Agent System (MAS) that simulates a classroom environment using three locally hosted Large Language Models (LLMs). One high-capacity model acts as the **Teacher**, while two lightweight models act as the **Students**. 

The simulation runs in continuous 20-minute "sprints" (simulating 1 hour of class), followed by 10-minute breaks where students interact socially, comfort each other, and write learning journals. A unique **Emotion & Memory System** tracks the students' psychological states (e.g., frustration, happiness) across sessions, dynamically influencing their responses and interactions.

---

## 📋 Product Backlog

### Epic 1: Infrastructure, Networking, and CI/CD
* **US 1: Classroom Setup (Controller Node)**
  * **As** Controller and Teacher, **I want to** simultaneously send prompts to the IP addresses of the Students' laptops using a Python script, **so that** we can start a synchronized 20-minute class session.
  * **Acceptance Criteria:** The script successfully pings both student IPs; the Teacher sends a lesson prompt, and both student LLMs return a response in the console.
* **US 2: Continuous Integration Pipeline (CI/CD)**
  * **As** a developer, **I want to** set up a GitHub Actions workflow, **so that** basic Python tests run automatically on every Push or Pull Request.
  * **Acceptance Criteria:** The `.github/workflows/main.yml` file is created; the repository shows a green checkmark on GitHub when the pushed Python code contains no syntax errors.
* **US 3: Asynchronous WebSocket Infrastructure**
  * **As** a system architect, **I want to** implement WebSockets (e.g., using `socketio` or `websockets`) instead of standard HTTP requests for the Controller-Node communication, **so that** the Student bots can stream their text asynchronously and simultaneously.
  * **Acceptance Criteria:** The Controller runs a WebSocket server; Student laptops connect as clients; the Controller can receive text streams from both students at the exact same time without blocking the main Python thread.

### Epic 2: Class Logic, Testing, and Breaks
* **US 4: Teaching, Testing, and Evaluation Log**
  * **As** the Teacher LLM, **I want to** teach a mini-lesson followed by a 10-question test at the end of each 20-minute sprint, and provide a written explanation for my grading, **so that** I can transparently evaluate the knowledge retained and justify the final marks.
  * **Acceptance Criteria:** The Teacher generates exactly 10 questions. The sprint number, generated questions, Students' answers, Teacher's grading reasoning, and final grades (1-10) are automatically saved into a `tests_log.json` or `.txt` file.
* **US 5: Live Break Interaction and Chat Logging**
  * **As** an observer (developer), **I want to** view the Students' 5-minute break conversation streamed live in a chatroom-style console and have it automatically saved to a log file afterwards, **so that** I can monitor their social dynamics in real-time and review the transcripts later.
  * **Acceptance Criteria:** A minimum of 5 replies per Student (10 messages total) are exchanged; the text streams to the Controller's screen in real-time with clear speaker tags (e.g., `[Phi-3]: Hey Qwen`); at the end of the break, the transcript is saved to `break_chat_log.txt`; bots refer to each other by their model names; a system prompt strictly forbids using keywords from the current class topic.
* **US 6: Learning Journal**
  * **As** a Student LLM, **I want to** generate a journal entry in the last 5 minutes of the break, **so that** I can summarize what I learned in under 1000 words and describe and justify my emotions.
  * **Acceptance Criteria:** The journal is saved locally as `journal_student_class1.txt`; the text is generated in the first person using the LLM's own name.
* **US 7: LLM Tool Calling & Function Execution**
  * **As** a Student LLM, **I want to** be able to call an external Python tool (like a calculator) during the 10-question test, **so that** I can accurately solve mathematical or logical problems beyond my base text-generation capabilities.
  * **Acceptance Criteria:** The Student's system prompt includes instructions to output a specific JSON format (e.g., `{"tool": "calculator", "equation": "5*12"}`) when needed; the Python script intercepts this JSON, executes the mathematical calculation, and feeds the result back to the LLM to formulate its final answer.

### Epic 3: Emotion and Memory System
* **US 8: Emotion Persistence**
  * **As** a Student LLM, **I want** my feelings to be saved in a `state.json` file at the end of each interaction, **so that** they can be injected as my "personality" prompt for the next class or break.
  * **Acceptance Criteria:** The JSON file updates variables like `frustration_prof: 8` or `happiness_peer: 5`; the Python script successfully loads these states into the next prompt.
* **US 9: Teacher Sanctions, Rewards, and Logging**
  * **As** the Teacher LLM, **I want to** be able to give sanctions or rewards to my students based on their answers, and save these actions along with a creative justification in a `teacher_log.json` file, **so that** I have a permanent, transparent record of my disciplinary actions.
  * **Acceptance Criteria:** The Teacher evaluates a student's response; a sanction or reward is generated with a creative text explanation (e.g., "Minus 2 points for falling asleep while Llama was talking"); the event is successfully appended to `teacher_log.json`; the targeted student's `frustration_prof` variable is updated accordingly in their state file.
* **US 10: Mutual Student Comforting**
  * **As** a Student LLM, **I want to** be able to comfort my classmate during the break if I notice they received a sanction, **so that** we can dynamically alter each other's emotional states in the `state.json` file.
  * **Acceptance Criteria:** During the break transcript, if Student 1 comforts Student 2 using their specific LLM name, Student 2's `frustration_prof` variable decreases by -1 in the `state.json` file.

### Epic 4: Automated Tests, Evals, and Bugs
* **US 11: Evals for the Journal (AI Test)**
  * **As** a QA Tester, **I want to** create an automated test, **so that** I can verify if the student journals always respect the 1000-word limit.
  * **Acceptance Criteria:** A Python script counts the words in the generated txt files; the test fails (FAIL) if the word count is > 1000.
* **US 12: Evals for Break Restrictions**
  * **As** a QA Tester, **I want** an automated test that analyzes the break transcripts against an array of `forbidden_words`, **so that** I can ensure the students didn't cheat by talking about the lesson.
  * **Acceptance Criteria:** The test checks the transcript against an array of forbidden words. If it finds a match, it flags a test failure.
* **US 13: Bug Reporting and Resolution via PR**
  * **As** a developer, **I want to** document a discovered bug in a GitHub Issue, **so that** I can fix it on a separate branch and merge it via a Pull Request.
  * **Acceptance Criteria:** There is at least one closed Issue and one PR tagged `bugfix` that has been reviewed and approved by another team member.

### Epic 5: Finalization and Reporting
* **US 14: The Scaling Experiment (3 hours vs 6 hours)**
  * **As** the research team, **We want to** run the system for 6 hours and compare the grades and emotional shifts with the 3-hour run, **so that** we can demonstrate whether the bots' performance increases or decreases over time.
  * **Acceptance Criteria:** Comparative charts or tables are generated from the CSV/JSON data and included in the final project report.
* **US 15: Automated Data Science Visualization**
  * **As** a data analyst, **I want to** automatically generate visual plots at the end of the 3-hour simulation, **so that** I can visually analyze the evolution of the students' academic knowledge and the correlation with their emotional shifts.
  * **Acceptance Criteria:** A Python script uses `matplotlib` or `seaborn` to parse the `tests_log.json` and `state.json` files; it successfully outputs two PNG graphs: one tracking grades over time (X-axis: Sprints, Y-axis: Grades) and one tracking emotional levels (X-axis: Sprints, Y-axis: Frustration/Happiness).

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
