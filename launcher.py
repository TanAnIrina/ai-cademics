"""
AI-cademics Launcher - One-command startup for the entire system.

Manages:
1. Ollama service health check
2. Required models verification
3. Database initialization
4. Backend FastAPI server
5. Frontend (React + Vite) dev server         <- NEW
6. (Optional) Student agents for local testing

Live progress (GET /api/live) requires backend/live_state.py + the patch
described in backend/MAIN_PY_PATCH.md applied to Main.py.

The frontend is auto-detected: if a `frontend/` folder exists, it starts by
default. Use --no-frontend to skip.

Usage:
    python launcher.py                          # Start backend + frontend
    python launcher.py --no-frontend            # Backend only
    python launcher.py --agents                 # + student agents on this machine
    python launcher.py --model gemma3:27b       # Specify teacher model
    python launcher.py --reset-db               # Reset database before starting
    python launcher.py --port 8000              # Backend port
    python launcher.py --frontend-port 5173     # Frontend port

Press Ctrl+C to gracefully shut down all processes.

Generated with Claude AI assistance.
"""

import subprocess
import sys
import os
import time
import signal
import argparse
import platform
import shutil
from pathlib import Path

# Try to import optional dependencies
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


# =============================================================================
# COLORS (cross-platform)
# =============================================================================

class Colors:
    """ANSI color codes that work on Windows 10+, Mac, Linux."""
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    MAGENTA = "\033[95m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"

    @staticmethod
    def enable_windows_colors():
        if platform.system() == "Windows":
            os.system("")  # Magic that enables ANSI on Win10+


def banner():
    print(f"\n{Colors.CYAN}{Colors.BOLD}")
    print("=" * 60)
    print("        AI-CADEMICS LAUNCHER  v1.1")
    print("        AI Classroom Simulation Orchestrator")
    print("=" * 60)
    print(f"{Colors.RESET}\n")


def step(num, total, message):
    print(f"{Colors.BLUE}[{num}/{total}]{Colors.RESET} {Colors.BOLD}{message}{Colors.RESET}")


def ok(message):    print(f"  {Colors.GREEN}OK{Colors.RESET} {message}")
def warn(message):  print(f"  {Colors.YELLOW}!{Colors.RESET}  {message}")
def err(message):   print(f"  {Colors.RED}X{Colors.RESET}  {message}")
def info(message):  print(f"  {Colors.DIM}>>{Colors.RESET} {message}")


# =============================================================================
# CHECKS
# =============================================================================

def check_python_version():
    major, minor = sys.version_info[:2]
    if (major, minor) < (3, 10):
        err(f"Python 3.10+ required, you have {major}.{minor}")
        return False
    ok(f"Python {major}.{minor} detected")
    return True


def check_ollama_running(host="http://localhost:11434"):
    if not HAS_REQUESTS:
        warn("requests library not installed - skipping Ollama check")
        return None
    try:
        r = requests.get(f"{host}/api/tags", timeout=3)
        if r.status_code == 200:
            ok(f"Ollama is running at {host}")
            return r.json()
        err(f"Ollama responded with status {r.status_code}")
        return False
    except requests.exceptions.ConnectionError:
        err(f"Ollama is NOT running at {host}")
        return False
    except Exception as e:
        err(f"Ollama check failed: {e}")
        return False


def _extract_model_names(ollama_data):
    if not ollama_data:
        return []
    names = []
    for m in ollama_data.get("models", []):
        name = m.get("name") or m.get("model") or ""
        if name:
            names.append(name)
    return names


def check_model_available(model_name, ollama_data):
    if not ollama_data:
        return False
    available_full = _extract_model_names(ollama_data)
    if model_name in available_full:
        ok(f"Model '{model_name}' is available")
        return True
    err(f"Model '{model_name}' NOT downloaded in Ollama")
    if available_full:
        info(f"Available models: {', '.join(available_full)}")
    info(f"Run: ollama pull {model_name}")
    return False


def check_dependencies():
    required = ["fastapi", "uvicorn", "ollama", "pydantic"]
    missing = []
    for package in required:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
    if missing:
        err(f"Missing packages: {', '.join(missing)}")
        info(f"Run: pip install {' '.join(missing)}")
        return False
    ok(f"All dependencies installed ({len(required)} packages)")
    return True


def check_files():
    backend_dir = Path("backend")
    if not backend_dir.exists():
        err("backend/ folder not found - run from project root!")
        return False

    required = ["main.py", "database.py"]
    optional = ["achievements.py", "streaming.py", "live_state.py"]

    found_required = [f for f in required if (backend_dir / f).exists()]
    found_optional = [f for f in optional if (backend_dir / f).exists()]

    if len(found_required) < len(required):
        missing = set(required) - set(found_required)
        err(f"Missing required files in backend/: {', '.join(missing)}")
        return False

    ok(f"Backend files: {', '.join(found_required + found_optional)}")

    # Notify about live progress feature status
    if "live_state.py" not in found_optional:
        warn("live_state.py not found - live progress endpoint /api/live will be unavailable")
        info("Drop live_state.py in backend/ and apply MAIN_PY_PATCH.md to enable it")
    return True


# ── Frontend checks ──────────────────────────────────────────────────────────

def npm_command():
    """Return the right npm executable for this OS."""
    return "npm.cmd" if platform.system() == "Windows" else "npm"


def check_frontend(frontend_dir: Path):
    """Verify frontend folder + node/npm are available. Returns True/False."""
    if not frontend_dir.exists():
        warn(f"{frontend_dir}/ folder not found - frontend will not start")
        return False

    npm_exe = shutil.which(npm_command())
    if not npm_exe:
        err("npm not found in PATH - install Node.js to start the frontend")
        info("Download: https://nodejs.org/")
        return False

    if not (frontend_dir / "package.json").exists():
        err(f"{frontend_dir}/package.json missing - is this the right folder?")
        return False

    ok(f"Frontend ready ({frontend_dir}/, npm at {npm_exe})")
    return True


def ensure_npm_install(frontend_dir: Path):
    """Run npm install if node_modules is missing."""
    node_modules = frontend_dir / "node_modules"
    if node_modules.exists():
        ok("node_modules already installed")
        return True
    info("node_modules missing - running npm install (this can take 30-60s)...")
    try:
        result = subprocess.run(
            [npm_command(), "install", "--no-audit", "--no-fund"],
            cwd=str(frontend_dir),
            check=True,
        )
        ok("npm install complete")
        return True
    except subprocess.CalledProcessError as e:
        err(f"npm install failed (exit {e.returncode})")
        return False
    except FileNotFoundError:
        err("npm not found - install Node.js")
        return False


# =============================================================================
# DATABASE
# =============================================================================

def init_database(reset=False):
    sys.path.insert(0, "backend")
    try:
        if reset:
            warn("Resetting database (--reset-db flag)")
            import database as db
            db.reset_database()
            ok("Database reset complete")
        else:
            import database as db  # auto-initializes on import
            stats = db.get_global_stats()
            ok(f"Database ready: {stats['total_sprints']} sprints, "
               f"{stats['total_questions_graded']} grades stored")
        return True
    except Exception as e:
        err(f"Database init failed: {e}")
        return False
    finally:
        if "backend" in sys.path:
            sys.path.remove("backend")


# =============================================================================
# PROCESS MANAGER
# =============================================================================

class ProcessManager:
    """Manages backend + frontend + agent subprocesses with graceful shutdown."""

    def __init__(self):
        self.processes = []
        self.shutdown_requested = False

    def start_backend(self, port=8000):
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        proc = subprocess.Popen(
            [sys.executable, "main.py"],
            cwd="backend",
            env=env,
        )
        self.processes.append(("Backend (FastAPI)", proc))
        return proc

    def start_frontend(self, frontend_dir: Path, port=5173):
        """Start Vite dev server. Cross-platform npm invocation."""
        env = os.environ.copy()
        env["PORT"] = str(port)
        env["VITE_PORT"] = str(port)
        # On Windows, use shell=True or .cmd; here we use the exe explicitly.
        cmd = [npm_command(), "run", "dev", "--", "--port", str(port)]
        # On Windows, Popen needs the resolved path or shell to find npm.cmd
        kwargs = {}
        if platform.system() == "Windows":
            kwargs["shell"] = False  # we're using .cmd directly
        proc = subprocess.Popen(
            cmd,
            cwd=str(frontend_dir),
            env=env,
            **kwargs,
        )
        self.processes.append(("Frontend (Vite)", proc))
        return proc

    def start_agent(self, name, model, backend_url="http://localhost:8000"):
        agents_dir = Path("agents")
        if not agents_dir.exists():
            warn(f"agents/ folder not found - skipping {name} agent")
            return None
        agent_script = agents_dir / "student_agent.py"
        if not agent_script.exists():
            warn(f"agents/student_agent.py not found - skipping {name} agent")
            return None
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        proc = subprocess.Popen(
            [sys.executable, str(agent_script), name, model, backend_url],
            env=env,
        )
        self.processes.append((f"Agent: {name} ({model})", proc))
        return proc

    def shutdown(self):
        if self.shutdown_requested:
            return
        self.shutdown_requested = True
        print(f"\n{Colors.YELLOW}Shutting down...{Colors.RESET}")
        # Shutdown in reverse order (frontend first, backend last) so the
        # frontend doesn't keep polling a dead backend
        for name, proc in reversed(self.processes):
            if proc.poll() is None:
                info(f"Stopping {name}...")
                try:
                    proc.terminate()
                    proc.wait(timeout=5)
                    ok(f"{name} stopped")
                except subprocess.TimeoutExpired:
                    proc.kill()
                    warn(f"{name} force-killed")
                except Exception as e:
                    err(f"{name} shutdown error: {e}")
        print(f"\n{Colors.GREEN}{Colors.BOLD}All processes stopped. Goodbye!{Colors.RESET}\n")

    def wait(self):
        try:
            while True:
                for name, proc in self.processes:
                    if proc.poll() is not None:
                        err(f"{name} exited with code {proc.returncode}")
                        return
                time.sleep(1)
        except KeyboardInterrupt:
            pass


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="AI-cademics Launcher - One-command startup",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--port", type=int, default=8000,
                        help="Backend port (default: 8000)")
    parser.add_argument("--frontend-port", type=int, default=5173,
                        help="Frontend dev server port (default: 5173)")
    parser.add_argument("--no-frontend", action="store_true",
                        help="Skip starting the React frontend")
    parser.add_argument("--model", default="gemma3:27b",
                        help="Teacher model name (default: gemma3:27b)")
    parser.add_argument("--agents", action="store_true",
                        help="Also start Qwen + Llama agents on this machine")
    parser.add_argument("--reset-db", action="store_true",
                        help="Reset database before starting (DANGER)")
    parser.add_argument("--skip-checks", action="store_true",
                        help="Skip pre-flight checks")
    parser.add_argument("--ollama-host", default="http://localhost:11434",
                        help="Ollama API host")

    args = parser.parse_args()

    Colors.enable_windows_colors()
    banner()

    frontend_dir = Path("frontend")
    want_frontend = (not args.no_frontend) and frontend_dir.exists()

    # Total step count depends on whether we're starting frontend
    total_steps = 6 if want_frontend else 5

    # ========================================================================
    # PRE-FLIGHT CHECKS
    # ========================================================================

    if not args.skip_checks:
        step(1, total_steps, "Pre-flight checks")

        if not check_python_version():        sys.exit(1)
        if not check_dependencies():          sys.exit(1)
        if not check_files():                 sys.exit(1)

        ollama_data = check_ollama_running(args.ollama_host)
        if ollama_data is False:
            print(f"\n{Colors.YELLOW}Tip: Start Ollama first:{Colors.RESET}")
            print(f"  Windows: Ollama tray app should already be running")
            print(f"  Manual: ollama serve")
            print()
            sys.exit(1)

        if ollama_data and not check_model_available(args.model, ollama_data):
            print(f"\n{Colors.YELLOW}Tip: Download the model first:{Colors.RESET}")
            print(f"  ollama pull {args.model}")
            print()
            sys.exit(1)

        if args.agents and ollama_data:
            check_model_available("qwen3:4b", ollama_data)
            check_model_available("llama3.2:3b", ollama_data)

        if want_frontend:
            if not check_frontend(frontend_dir):
                warn("Frontend will be skipped (use --no-frontend to silence this)")
                want_frontend = False
                total_steps = 5

        print()

    # ========================================================================
    # DATABASE
    # ========================================================================

    step(2, total_steps, "Database initialization")
    if not init_database(reset=args.reset_db):
        sys.exit(1)
    print()

    # ========================================================================
    # FRONTEND PREP (npm install if needed) - done before starting subprocesses
    # ========================================================================

    if want_frontend:
        step(3, total_steps, "Frontend preparation")
        if not ensure_npm_install(frontend_dir):
            warn("Frontend skipped due to npm install failure")
            want_frontend = False
            total_steps -= 1
        print()

    # ========================================================================
    # START PROCESSES
    # ========================================================================

    manager = ProcessManager()

    def signal_handler(signum, frame):
        manager.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, signal_handler)

    # Backend
    backend_step = 4 if want_frontend else 3
    step(backend_step, total_steps, "Starting backend server")
    info(f"FastAPI backend on port {args.port}")
    manager.start_backend(port=args.port)
    time.sleep(3)

    # Verify backend
    if HAS_REQUESTS:
        try:
            r = requests.get(f"http://localhost:{args.port}/", timeout=5)
            if r.status_code == 200:
                ok(f"Backend is responding at http://localhost:{args.port}")
                # Verify live endpoint if live_state.py is present
                if (Path("backend") / "live_state.py").exists():
                    try:
                        rl = requests.get(f"http://localhost:{args.port}/api/live", timeout=2)
                        if rl.status_code == 200:
                            ok("Live progress endpoint /api/live is wired up")
                        else:
                            warn(f"/api/live returned {rl.status_code} - did you apply MAIN_PY_PATCH.md?")
                    except Exception:
                        warn("/api/live not reachable - did you apply MAIN_PY_PATCH.md to Main.py?")
            else:
                warn(f"Backend status: {r.status_code}")
        except Exception:
            warn("Backend not responding yet (might still be starting)")
    print()

    # Frontend
    if want_frontend:
        frontend_step = 5
        step(frontend_step, total_steps, "Starting frontend dev server")
        info(f"Vite dev server on port {args.frontend_port}")
        manager.start_frontend(frontend_dir, port=args.frontend_port)
        # Vite usually takes 1-3s to be ready
        time.sleep(3)
        if HAS_REQUESTS:
            try:
                r = requests.get(f"http://localhost:{args.frontend_port}/", timeout=3)
                if r.status_code in (200, 304):
                    ok(f"Frontend is responding at http://localhost:{args.frontend_port}")
                else:
                    warn(f"Frontend status: {r.status_code} (might still be warming up)")
            except Exception:
                warn("Frontend not responding yet (might still be starting)")
        print()

    # Agents (optional)
    agents_step = total_steps - 1
    if args.agents:
        step(agents_step, total_steps, "Starting student agents (local mode)")
        manager.start_agent("Qwen", "qwen3:4b", f"http://localhost:{args.port}")
        time.sleep(1)
        manager.start_agent("Llama", "llama3.2:3b", f"http://localhost:{args.port}")
        time.sleep(2)
        ok("Agents running")
        print()
    else:
        step(agents_step, total_steps, "Skipping agents (running on remote laptops)")
        info("Colegii pornesc agentii pe laptopurile lor:")
        info(f"  python agents/student_agent.py Qwen qwen3:4b http://<your-ip>:{args.port}")
        info(f"  python agents/student_agent.py Llama llama3.2:3b http://<your-ip>:{args.port}")
        print()

    # ========================================================================
    # READY STATUS
    # ========================================================================

    step(total_steps, total_steps, "System ready!")
    print()
    if want_frontend:
        print(f"  {Colors.BOLD}>> Frontend UI:{Colors.RESET}      "
              f"{Colors.CYAN}http://localhost:{args.frontend_port}{Colors.RESET}   "
              f"{Colors.DIM}(open this in your browser){Colors.RESET}")
    print(f"  {Colors.BOLD}>> Backend URL:{Colors.RESET}      http://localhost:{args.port}")
    print(f"  {Colors.BOLD}>> Swagger UI:{Colors.RESET}       http://localhost:{args.port}/docs")
    print(f"  {Colors.BOLD}>> Live progress:{Colors.RESET}    http://localhost:{args.port}/api/live")
    print(f"  {Colors.BOLD}>> Leaderboard:{Colors.RESET}      http://localhost:{args.port}/api/leaderboard")
    print(f"  {Colors.BOLD}>> Stats:{Colors.RESET}            http://localhost:{args.port}/api/stats")
    print()
    print(f"  {Colors.DIM}Press Ctrl+C to stop everything{Colors.RESET}")
    print()
    print(f"{Colors.CYAN}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.MAGENTA}>> Live logs from backend{' + frontend' if want_frontend else ''} below:{Colors.RESET}")
    print(f"{Colors.CYAN}{'=' * 60}{Colors.RESET}")
    print()

    manager.wait()
    manager.shutdown()


if __name__ == "__main__":
    main()
