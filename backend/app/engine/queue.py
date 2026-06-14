"""Task queue for the optional self-hosted ('external') agent runtime.

Mirrors the original AI-cademics poll/submit protocol: the backend enqueues a
task for an agent, the agent process polls for it, runs its own local model, and
submits the answer. Kept entirely in memory and scoped per (classroom, agent).
"""
from __future__ import annotations

import threading
import time
import uuid
from collections import defaultdict, deque


class ExternalQueue:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._tasks: dict[tuple[int, str], deque] = defaultdict(deque)
        self._responses: dict[str, str] = {}

    def enqueue(self, classroom_id: int, agent_name: str, system_prompt: str,
                prompt: str, mode: str) -> str:
        task_id = str(uuid.uuid4())
        task = {
            "task_id": task_id,
            "system_prompt": system_prompt,
            "prompt": prompt,
            "mode": mode,
        }
        with self._lock:
            self._tasks[(classroom_id, agent_name)].append(task)
        return task_id

    def poll(self, classroom_id: int, agent_name: str) -> dict | None:
        with self._lock:
            q = self._tasks.get((classroom_id, agent_name))
            if q:
                return q.popleft()
        return None

    def submit(self, task_id: str, content: str) -> None:
        with self._lock:
            self._responses[task_id] = content

    def dispatch_and_wait(self, classroom_id: int, agent_name: str,
                          system_prompt: str, prompt: str, mode: str,
                          timeout: float = 120.0, interval: float = 0.5) -> str | None:
        task_id = self.enqueue(classroom_id, agent_name, system_prompt, prompt, mode)
        deadline = time.time() + timeout
        while time.time() < deadline:
            with self._lock:
                if task_id in self._responses:
                    return self._responses.pop(task_id)
            time.sleep(interval)
        return None


class BoundQueue:
    """A view of :class:`ExternalQueue` pinned to a single classroom."""

    def __init__(self, queue: ExternalQueue, classroom_id: int) -> None:
        self._queue = queue
        self._classroom_id = classroom_id

    def dispatch_and_wait(self, agent_name: str, system_prompt: str,
                          prompt: str, mode: str) -> str | None:
        return self._queue.dispatch_and_wait(
            self._classroom_id, agent_name, system_prompt, prompt, mode
        )


# Module-level singleton.
external_queue = ExternalQueue()
