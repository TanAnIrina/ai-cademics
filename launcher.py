"""
AI-cademics Launcher - One-command startup for the entire system.

Manages:
1. Ollama service health check
2. Required models verification  
3. Database initialization
4. Backend FastAPI server
5. (Optional) Student agents for local testing

Usage:
    python launcher.py                        # Start backend only (typical for Bianca's laptop)
    python launcher.py --agents               # Also start Qwen + Llama agents locally (for solo testing)
    python launcher.py --model gemma3:27b     # Specify teacher model
    python launcher.py --reset-db             # Reset database before starting
    python launcher.py --port 8000            # Custom port

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
        """Enable ANSI colors on Windows 10+."""
        if platform.system() == "Windows":
            os.system("")  # Magic that enables ANSI on Win10+


def banner():
    """Print startup banner."""
    print(f"\n{Colors.CYAN}{Colors.BOLD}")
    print("=" * 60)
    print("        AI-CADEMICS LAUNCHER  v1.0")
    print("        AI Classroom Simulation Orchestrator")
    print("=" * 60)
    print(f"{Colors.RESET}\n")


def step(num, total, message):
    """Print step header."""
    print(f"{Colors.BLUE}[{num}/{total}]{Colors.RESET} {Colors.BOLD}{message}{Colors.RESET}")


def ok(message):
    print(f"  {Colors.GREEN}OK{Colors.RESET} {message}")


def warn(message):
    print(f"  {Colors.YELLOW}!{Colors.RESET}  {message}")


def err(message):
    print(f"  {Colors.RED}X{Colors.RESET}  {message}")


def info(message):
    print(f"  {Colors.DIM}>>{Colors.RESET} {message}")


# =============================================================================
# CHECKS
# =============================================================================

def check_python_version():
    """Verify Python 3.10+."""
    major, minor = sys.version_info[:2]
    if (major, minor) < (3, 10):
        err(f"Python 3.10+ required, you have {major}.{minor}")
        return False
    ok(f"Python {major}.{minor} detected")
    return True


def check_ollama_running(host="http://localhost:11434"):
    """Check if Ollama is running."""
    if not HAS_REQUESTS:
        warn("requests library not installed - skipping Ollama check")
        return None
    
    try:
        r = requests.get(f"{host}/api/tags", timeout=3)
        if r.status_code == 200:
            ok(f"Ollama is running at {host}")
            return r.json()
        else:
            err(f"Ollama responded with status {r.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        err(f"Ollama is NOT running at {host}")
        return False
    except Exception as e:
        err(f"Ollama check failed: {e}")
        return False


def _extract_model_names(ollama_data):
    """
    Extract model name strings from /api/tags response.
    
    Different Ollama versions populate either 'name' or 'model' (or both),
    so we accept whichever is present.
    """
    if not ollama_data:
        return []
    models = ollama_data.get("models", [])
    names = []
    for m in models:
        name = m.get("name") or m.get("model") or ""
        if name:
            names.append(name)
    return names


def check_model_available(model_name, ollama_data):
    """Check if a specific model is downloaded in Ollama."""
    if not ollama_data:
        return False
    
    available_full = _extract_model_names(ollama_data)
    
    # Exact tag match (e.g. "gemma3:27b" must match exactly)
    if model_name in available_full:
        ok(f"Model '{model_name}' is available")
        return True
    
    err(f"Model '{model_name}' NOT downloaded in Ollama")
    if available_full:
        info(f"Available models: {', '.join(available_full)}")
    info(f"Run: ollama pull {model_name}")
    return False


def check_dependencies():
    """Check required Python packages."""
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
    """Check required project files exist."""
    backend_dir = Path("backend")
    if not backend_dir.exists():
        err("backend/ folder not found - run from project root!")
        return False
    
    required = ["main.py", "database.py"]
    optional = ["achievements.py", "streaming.py"]
    
    found_required = [f for f in required if (backend_dir / f).exists()]
    found_optional = [f for f in optional if (backend_dir / f).exists()]
    
    if len(found_required) < len(required):
        missing = set(required) - set(found_required)
        err(f"Missing required files in backend/: {', '.join(missing)}")
        return False
    
    ok(f"Backend files: {', '.join(found_required + found_optional)}")
    return True


# =============================================================================
# DATABASE
# =============================================================================

def init_database(reset=False):
    """Initialize or reset the SQLite database."""
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
    """Manages backend + agent subprocesses with graceful shutdown."""
    
    def __init__(self):
        self.processes = []
        self.shutdown_requested = False
    
    def start_backend(self, port=8000):
        """Start FastAPI backend."""
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        
        proc = subprocess.Popen(
            [sys.executable, "main.py"],
            cwd="backend",
            env=env
        )
        self.processes.append(("Backend (FastAPI)", proc))
        return proc
    
    def start_agent(self, name, model, backend_url="http://localhost:8000"):
        """Start a student agent."""
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
            env=env
        )
        self.processes.append((f"Agent: {name} ({model})", proc))
        return proc
    
    def shutdown(self):
        """Gracefully terminate all processes."""
        if self.shutdown_requested:
            return
        self.shutdown_requested = True
        
        print(f"\n{Colors.YELLOW}Shutting down...{Colors.RESET}")
        for name, proc in self.processes:
            if proc.poll() is None:  # still running
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
        """Wait for processes (blocking)."""
        try:
            while True:
                # Check if any process died
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
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--port", type=int, default=8000,
                          help="Backend port (default: 8000)")
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
    
    # ========================================================================
    # PRE-FLIGHT CHECKS
    # ========================================================================
    
    if not args.skip_checks:
        step(1, 5, "Pre-flight checks")
        
        if not check_python_version():
            sys.exit(1)
        
        if not check_dependencies():
            sys.exit(1)
        
        if not check_files():
            sys.exit(1)
        
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
        
        print()
    
    # ========================================================================
    # DATABASE
    # ========================================================================
    
    step(2, 5, "Database initialization")
    if not init_database(reset=args.reset_db):
        sys.exit(1)
    print()
    
    # ========================================================================
    # START PROCESSES
    # ========================================================================
    
    manager = ProcessManager()
    
    # Register cleanup
    def signal_handler(signum, frame):
        manager.shutdown()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, signal_handler)
    
    # Start backend
    step(3, 5, "Starting backend server")
    info(f"FastAPI backend on port {args.port}")
    manager.start_backend(port=args.port)
    
    # Wait a moment for backend to come up
    time.sleep(3)
    
    # Verify backend is up
    if HAS_REQUESTS:
        try:
            r = requests.get(f"http://localhost:{args.port}/", timeout=5)
            if r.status_code == 200:
                ok(f"Backend is responding at http://localhost:{args.port}")
            else:
                warn(f"Backend status: {r.status_code}")
        except Exception:
            warn("Backend not responding yet (might still be starting)")
    print()
    
    # Start agents (optional)
    if args.agents:
        step(4, 5, "Starting student agents (local mode)")
        manager.start_agent("Qwen", "qwen3:4b", f"http://localhost:{args.port}")
        time.sleep(1)
        manager.start_agent("Llama", "llama3.2:3b", f"http://localhost:{args.port}")
        time.sleep(2)
        ok("Agents running")
        print()
    else:
        step(4, 5, "Skipping agents (running on remote laptops)")
        info("Colegii pornesc agentii pe laptopurile lor:")
        info(f"  python agents/student_agent.py Qwen qwen3:4b http://<your-ip>:{args.port}")
        info(f"  python agents/student_agent.py Llama llama3.2:3b http://<your-ip>:{args.port}")
        print()
    
    # ========================================================================
    # READY STATUS
    # ========================================================================
    
    step(5, 5, "System ready!")
    print()
    print(f"  {Colors.BOLD}>> URL:{Colors.RESET}              http://localhost:{args.port}")
    print(f"  {Colors.BOLD}>> Swagger UI:{Colors.RESET}       http://localhost:{args.port}/docs")
    print(f"  {Colors.BOLD}>> WebSocket:{Colors.RESET}        ws://localhost:{args.port}/ws")
    print(f"  {Colors.BOLD}>> Leaderboard:{Colors.RESET}      http://localhost:{args.port}/api/leaderboard")
    print(f"  {Colors.BOLD}>> Stats:{Colors.RESET}            http://localhost:{args.port}/api/stats")
    print()
    print(f"  {Colors.DIM}Press Ctrl+C to stop everything{Colors.RESET}")
    print()
    print(f"{Colors.CYAN}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.MAGENTA}>> Live logs from backend below:{Colors.RESET}")
    print(f"{Colors.CYAN}{'=' * 60}{Colors.RESET}")
    print()
    
    # ========================================================================
    # WAIT FOR PROCESSES
    # ========================================================================
    
    manager.wait()
    manager.shutdown()


if __name__ == "__main__":
    main()
