"""Versioned adaptation-session records with immutable finalized artifacts."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import socket
from typing import Any, Mapping


def file_sha256(path: Path) -> str:
    """Return the SHA-256 identity of a file."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class AdaptationSession:
    """Write policy decisions and episode summaries without hardware access."""

    def __init__(
        self,
        output_dir: Path,
        *,
        champion_checkpoint: Path,
        helper_checkpoint: Path | None = None,
        mode: str = "shadow",
        metadata: Mapping[str, Any] | None = None,
    ):
        """Create a new recording directory and bind its policy identities."""
        if mode not in {"disabled", "shadow", "bounded"}:
            raise ValueError("unsupported adaptation mode")
        champion_checkpoint = champion_checkpoint.resolve()
        if not champion_checkpoint.is_file():
            raise FileNotFoundError(champion_checkpoint)
        helper_checkpoint = (
            helper_checkpoint.resolve()
            if helper_checkpoint is not None
            else None
        )
        if helper_checkpoint is not None and not helper_checkpoint.is_file():
            raise FileNotFoundError(helper_checkpoint)
        self.output_dir = output_dir.resolve()
        self.output_dir.mkdir(parents=True, exist_ok=False)
        self._steps_path = self.output_dir / "steps.jsonl.partial"
        self._episodes_path = self.output_dir / "episodes.jsonl.partial"
        self._steps = self._steps_path.open("w", encoding="utf-8")
        self._episodes = self._episodes_path.open("w", encoding="utf-8")
        self._step_count = 0
        self._episode_count = 0
        self._finished = False
        self._manifest = {
            "schema_version": 1,
            "completed": False,
            "publishes_commands": False,
            "mode": mode,
            "started_utc": datetime.now(timezone.utc).isoformat(),
            "hostname": socket.gethostname(),
            "champion": {
                "path": str(champion_checkpoint),
                "sha256": file_sha256(champion_checkpoint),
            },
            "helper": (
                {
                    "path": str(helper_checkpoint),
                    "sha256": file_sha256(helper_checkpoint),
                }
                if helper_checkpoint is not None
                else None
            ),
            "metadata": dict(metadata or {}),
        }
        self._write_manifest()

    @staticmethod
    def _jsonable(record: Any) -> Any:
        return asdict(record) if is_dataclass(record) else record

    def _write(self, stream, record: Any) -> None:
        stream.write(
            json.dumps(self._jsonable(record), allow_nan=False, sort_keys=True)
            + "\n"
        )
        stream.flush()

    def write_step(self, record: Mapping[str, Any] | Any) -> None:
        """Append and flush one synchronized policy decision."""
        if self._finished:
            raise RuntimeError("session is finalized")
        self._write(self._steps, record)
        self._step_count += 1

    def write_episode(self, record: Mapping[str, Any] | Any) -> None:
        """Append and flush one episode outcome and weakness summary."""
        if self._finished:
            raise RuntimeError("session is finalized")
        self._write(self._episodes, record)
        self._episode_count += 1

    def _write_manifest(self) -> None:
        temporary = self.output_dir / "manifest.json.tmp"
        temporary.write_text(
            json.dumps(self._manifest, indent=2, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, self.output_dir / "manifest.json")

    def finish(self) -> Path:
        """Finalize streams, hashes, counts, and the complete manifest."""
        if self._finished:
            return self.output_dir / "manifest.json"
        self._steps.close()
        self._episodes.close()
        steps = self.output_dir / "steps.jsonl"
        episodes = self.output_dir / "episodes.jsonl"
        os.replace(self._steps_path, steps)
        os.replace(self._episodes_path, episodes)
        self._manifest.update(
            {
                "completed": True,
                "finished_utc": datetime.now(timezone.utc).isoformat(),
                "counts": {
                    "steps": self._step_count,
                    "episodes": self._episode_count,
                },
                "artifacts": {
                    "steps.jsonl": file_sha256(steps),
                    "episodes.jsonl": file_sha256(episodes),
                },
            }
        )
        self._write_manifest()
        self._finished = True
        return self.output_dir / "manifest.json"

    def __enter__(self) -> "AdaptationSession":
        """Return this active session."""
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        """Finalize successful sessions and retain partial failed sessions."""
        if exc_type is None:
            self.finish()
        else:
            self._steps.close()
            self._episodes.close()
