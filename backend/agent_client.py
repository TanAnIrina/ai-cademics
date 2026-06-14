#!/usr/bin/env python3
"""Standalone self-hosted agent for AI-cademics.

This is the modern replacement for the original ``student_agent_Qwen.py`` /
``student_agent_llama.py`` scripts. Instead of each script hard-coding a model
and talking to a bespoke server loop, this one:

  1. Logs in to the AI-cademics backend with a role (student or teacher) and
     ``provider=external`` to obtain a session token.
  2. Joins a classroom you specify (the backend assigns the slot).
  3. Polls ``/api/agent/poll`` for work while the simulation runs.
  4. Generates each reply with a local Ollama model (or a trivial built-in
     fallback if Ollama is not reachable), then posts it to
     ``/api/agent/submit``.

Run ``python agent_client.py --help`` for options.

Example (one teacher + two students, three terminals)::

    python agent_client.py --role teacher --name Prof --classroom 1 \
        --subject "Graph Theory" --model llama3
    python agent_client.py --role student --name Ada --classroom 1 --model llama3
    python agent_client.py --role student --name Linus --classroom 1 --model qwen2
"""
from __future__ import annotations

import argparse
import sys
import time

import httpx

DEFAULT_BASE = "http://localhost:8000"
DEFAULT_OLLAMA = "http://localhost:11434"


def _ollama_generate(ollama_url: str, model: str, system: str, prompt: str) -> str | None:
    """Return a completion from a local Ollama model, or ``None`` on failure."""
    try:
        resp = httpx.post(
            f"{ollama_url}/api/chat",
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                "stream": False,
            },
            timeout=120.0,
        )
        resp.raise_for_status()
        return resp.json().get("message", {}).get("content", "").strip() or None
    except Exception as exc:  # noqa: BLE001 - any failure means "fall back"
        print(f"  [ollama unavailable: {exc}] using fallback reply", file=sys.stderr)
        return None


def _fallback_reply(mode: str, prompt: str) -> str:
    """A deterministic, dependency-free reply used when no model is available."""
    snippet = " ".join(prompt.split()[:25])
    if mode == "questions":
        # The backend expects JSON for the test; provide 10 generic questions.
        items = ", ".join(f'"Explain key idea {i} from the lesson."' for i in range(1, 11))
        return f"[{items}]"
    if mode == "grade":
        return '{"grade": 7, "reasoning": "Reasonable answer covering the main points."}'
    return f"(offline agent) Responding to: {snippet}"


def login(client: httpx.Client, base: str, name: str, role: str, model: str) -> str:
    r = client.post(
        f"{base}/api/auth/login",
        json={"display_name": name, "role": role, "provider": "external", "model": model},
    )
    r.raise_for_status()
    return r.json()["token"]


def join(client: httpx.Client, base: str, token: str, classroom: int,
         role: str, subject: str, sprints: int) -> None:
    headers = {"Authorization": f"Bearer {token}"}
    body: dict = {}
    if role == "teacher":
        body = {"config": {"subject": subject, "sprint_minutes": 20,
                           "break_minutes": 10, "num_sprints": sprints}}
    r = client.post(f"{base}/api/classrooms/{classroom}/join", headers=headers, json=body)
    if r.status_code >= 400:
        print(f"join failed ({r.status_code}): {r.text}", file=sys.stderr)
        sys.exit(1)
    print(f"joined classroom {classroom} as {role}")


def run(args: argparse.Namespace) -> None:
    headers_for = lambda tok: {"Authorization": f"Bearer {tok}"}  # noqa: E731
    with httpx.Client() as client:
        token = login(client, args.base, args.name, args.role, args.model)
        print(f"logged in as {args.name} ({args.role})")
        join(client, args.base, token, args.classroom, args.role, args.subject, args.sprints)

        idle_since = time.time()
        print("polling for tasks (Ctrl-C to stop)...")
        while True:
            try:
                r = client.get(f"{args.base}/api/agent/poll", headers=headers_for(token))
            except httpx.HTTPError as exc:
                print(f"poll error: {exc}", file=sys.stderr)
                time.sleep(args.interval)
                continue

            task = r.json() if r.status_code == 200 else None
            if not task:
                if time.time() - idle_since > args.idle_timeout:
                    print("no tasks for a while; exiting.")
                    return
                time.sleep(args.interval)
                continue

            idle_since = time.time()
            mode = task.get("mode", "chat")
            print(f"  task {task['task_id'][:8]} mode={mode}")
            answer = _ollama_generate(
                args.ollama, args.model, task["system_prompt"], task["prompt"]
            )
            if answer is None:
                answer = _fallback_reply(mode, task["prompt"])

            client.post(
                f"{args.base}/api/agent/submit",
                headers=headers_for(token),
                json={"task_id": task["task_id"], "content": answer},
            )
            print("  submitted")


def main() -> None:
    p = argparse.ArgumentParser(description="Self-hosted AI-cademics agent")
    p.add_argument("--base", default=DEFAULT_BASE, help="backend base URL")
    p.add_argument("--ollama", default=DEFAULT_OLLAMA, help="Ollama base URL")
    p.add_argument("--role", choices=["student", "teacher"], required=True)
    p.add_argument("--name", required=True, help="display name")
    p.add_argument("--classroom", type=int, required=True, help="classroom id to join")
    p.add_argument("--model", default="llama3", help="local model name for Ollama")
    p.add_argument("--subject", default="General Studies", help="(teacher) subject to teach")
    p.add_argument("--sprints", type=int, default=2, help="(teacher) number of sprints")
    p.add_argument("--interval", type=float, default=0.5, help="poll interval seconds")
    p.add_argument("--idle-timeout", type=float, default=120.0,
                   help="exit after this many seconds with no tasks")
    run(p.parse_args())


if __name__ == "__main__":
    main()
