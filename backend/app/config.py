"""Application configuration.

All values can be overridden via environment variables (prefixed with ``AICADEMICS_``)
or a local ``.env`` file. See ``.env.example`` at the repo root.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AICADEMICS_",
        env_file=".env",
        extra="ignore",
    )

    # Database -----------------------------------------------------------------
    database_url: str = "sqlite:///./aicademics.db"

    # CORS ---------------------------------------------------------------------
    # Comma separated list of allowed origins for the browser frontend.
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Simulation ---------------------------------------------------------------
    # Seconds the engine pauses between *minor* steps (test answers, each grade,
    # each journal). Kept small; lesson/break length is driven by time_scale below.
    sim_phase_seconds: float = 0.4
    # Real-time multiplier for the teaching and break phases. With 1.0 a 20-minute
    # sprint's lesson actually spans ~20 minutes of paced discussion; lower it to
    # compress a session for demos/CI (tests use 0 = instant).
    time_scale: float = 1.0
    # How long the engine waits for the teacher to choose the next sprint's subject
    # before keeping the current one (0 = don't pause, used in tests).
    subject_choice_seconds: float = 180.0
    # How many break-chat turns the two students exchange.
    break_turns: int = 4
    # Number of demo classrooms seeded on first startup.
    seed_classrooms: int = 3

    # Defaults a teacher may override when configuring a classroom.
    default_sprint_minutes: int = 20
    default_break_minutes: int = 10
    default_num_sprints: int = 2

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
