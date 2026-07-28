"""External fixed-step validation monitor for a running DreamerV3 job."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any


def latest_metric_step(metrics_path: Path) -> int:
    latest = -1
    if not metrics_path.is_file():
        return latest
    with metrics_path.open("r", encoding="utf-8") as stream:
        for line in stream:
            try:
                latest = max(latest, int(json.loads(line).get("step", -1)))
            except (ValueError, json.JSONDecodeError):
                continue
    return latest


def checkpoint_signature(path: Path) -> tuple[int, int] | None:
    if not path.is_file() or path.with_name(path.name + ".old").exists():
        return None
    stat = path.stat()
    return stat.st_size, stat.st_mtime_ns


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def wait_for_stable_snapshot(
    source: Path,
    destination: Path,
    previous_signature: tuple[int, int] | None,
    poll_seconds: float,
) -> str:
    """Copy the first new stable checkpoint without racing its writer."""

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    while True:
        first = checkpoint_signature(source)
        if first is None or first == previous_signature:
            time.sleep(poll_seconds)
            continue
        time.sleep(min(5.0, poll_seconds))
        second = checkpoint_signature(source)
        if first != second:
            continue
        shutil.copy2(source, temporary)
        third = checkpoint_signature(source)
        if third != second or temporary.stat().st_size != second[0]:
            temporary.unlink(missing_ok=True)
            continue
        digest = sha256(temporary)
        os.replace(temporary, destination)
        destination.with_suffix(".sha256").write_text(
            f"{digest}  {destination.name}\n", encoding="utf-8"
        )
        return digest


def gpu_available(gpu: int, memory_limit_mib: int, utilization_limit: int) -> bool:
    command = [
        "nvidia-smi",
        "-i",
        str(gpu),
        "--query-gpu=memory.used,utilization.gpu",
        "--format=csv,noheader,nounits",
    ]
    try:
        output = subprocess.check_output(command, text=True, timeout=15).strip()
        memory, utilization = [int(value.strip()) for value in output.split(",")]
        return memory <= memory_limit_mib and utilization <= utilization_limit
    except (OSError, ValueError, subprocess.SubprocessError):
        return False


def wait_for_gpu(
    gpu: int,
    poll_seconds: float,
    memory_limit_mib: int,
    utilization_limit: int,
) -> None:
    while not gpu_available(gpu, memory_limit_mib, utilization_limit):
        print(f"GPU {gpu} is busy; waiting.", flush=True)
        time.sleep(poll_seconds)


def evaluator_command(
    args: argparse.Namespace,
    snapshot: Path,
    milestone_dir: Path,
    trigger_step: int,
    mode: str,
) -> list[str]:
    episodes = 1 if mode == "canonical" else args.robust_episodes_per_maze
    return [
        str(args.python),
        str(args.repo_root / "dreamerv3/dreamerv3/eval_multimaze.py"),
        "--checkpoint",
        str(snapshot),
        "--config",
        str(args.run_dir / "config.yaml"),
        "--manifest",
        str(args.manifest),
        "--split",
        "validation",
        "--mode",
        mode,
        "--episodes-per-maze",
        str(episodes),
        "--max-steps",
        str(args.max_steps),
        "--seed",
        str(args.seed),
        "--trigger-step",
        str(trigger_step),
        "--output",
        str(milestone_dir / f"{mode}.json"),
    ]


def launch_evaluator(
    args: argparse.Namespace,
    snapshot: Path,
    milestone_dir: Path,
    trigger_step: int,
    mode: str,
    gpu: int,
) -> tuple[subprocess.Popen[str], Any]:
    log_path = milestone_dir / f"{mode}.log"
    log_stream = log_path.open("w", encoding="utf-8")
    environment = os.environ.copy()
    environment.update(
        CUDA_VISIBLE_DEVICES=str(gpu),
        XLA_PYTHON_CLIENT_PREALLOCATE="false",
        MUJOCO_GL="egl",
        PYTHONUNBUFFERED="1",
    )
    command = evaluator_command(args, snapshot, milestone_dir, trigger_step, mode)
    print(f"Launching {mode} validation on physical GPU {gpu}.", flush=True)
    process = subprocess.Popen(
        command,
        cwd=args.repo_root,
        env=environment,
        stdout=log_stream,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return process, log_stream


def append_history(validation_root: Path, result: dict[str, Any]) -> None:
    summary = result["summary"]
    row = {
        "trigger_step": result["trigger_step"],
        "checkpoint_step": result["checkpoint_step"],
        "mode": result["mode"],
        "episodes": summary["episodes"],
        "completion_rate": summary["completion_rate"],
        "fall_rate": summary["fall_rate"],
        "mean_max_route_completion": summary["mean_max_route_completion"],
        "mean_final_route_completion": summary["mean_final_route_completion"],
        "mean_cross_track_error_m": summary["mean_cross_track_error_m"],
        "minimum_clearance_m": summary["minimum_clearance_m"],
        "mean_return": summary["mean_return"],
        "mean_steps_to_goal": summary["mean_steps_to_goal"],
        "duration_seconds": result["duration_seconds"],
        "checkpoint_sha256": result["checkpoint_sha256"],
    }
    history_jsonl = validation_root / "history.jsonl"
    with history_jsonl.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(row, allow_nan=False) + "\n")
    history_csv = validation_root / "history.csv"
    create_header = not history_csv.exists()
    with history_csv.open("a", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(row))
        if create_header:
            writer.writeheader()
        writer.writerow(row)

    if result["mode"] == "canonical":
        best_path = validation_root / "best_checkpoint.json"
        current = json.loads(best_path.read_text()) if best_path.exists() else None

        def rank(item: dict[str, Any]) -> tuple[float, ...]:
            values = item["summary"]
            return (
                float(values["completion_rate"] or 0.0),
                -float(values["fall_rate"] or 0.0),
                float(values["mean_max_route_completion"] or 0.0),
                -float(values["mean_cross_track_error_m"] or 1e9),
            )

        if current is None or rank(result) > rank(current):
            best_path.write_text(
                json.dumps(result, indent=2, allow_nan=False) + "\n",
                encoding="utf-8",
            )


def completed_modes(milestone_dir: Path) -> set[str]:
    complete = set()
    for mode in ("canonical", "robust"):
        path = milestone_dir / f"{mode}.json"
        if path.exists() and json.loads(path.read_text()).get("completed"):
            complete.add(mode)
    return complete


def milestones(start: int, interval: int, end: int, baseline: bool) -> list[int]:
    values = list(range(start, end + 1, interval))
    if baseline and 0 not in values:
        values.insert(0, 0)
    return values


def requires_new_checkpoint(trigger_step: int, end_step: int) -> bool:
    """Intermediate milestones need a post-trigger write; endpoints do not."""

    return trigger_step not in {0, end_step}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--start-step", type=int, default=500_000)
    parser.add_argument("--interval", type=int, default=500_000)
    parser.add_argument("--robust-interval", type=int, default=1_000_000)
    parser.add_argument("--end-step", type=int, default=10_000_000)
    parser.add_argument("--baseline", action="store_true")
    parser.add_argument("--canonical-gpu", type=int, default=3)
    parser.add_argument("--robust-gpu", type=int, default=4)
    parser.add_argument("--robust-episodes-per-maze", type=int, default=3)
    parser.add_argument("--max-steps", type=int, default=3000)
    parser.add_argument("--seed", type=int, default=20260723)
    parser.add_argument("--poll-seconds", type=float, default=30.0)
    parser.add_argument("--final-checkpoint-grace-seconds", type=float, default=120.0)
    parser.add_argument("--gpu-memory-limit-mib", type=int, default=5000)
    parser.add_argument("--gpu-utilization-limit", type=int, default=10)
    args = parser.parse_args()

    args.repo_root = args.repo_root.resolve()
    args.run_dir = args.run_dir.resolve()
    args.manifest = (
        args.manifest.resolve()
        if args.manifest
        else (args.repo_root / "tag_mujoco/maze_splits.json").resolve()
    )
    if not args.manifest.is_file():
        raise FileNotFoundError(args.manifest)
    # Do not resolve the virtualenv interpreter symlink: resolving it can turn
    # `.venv/bin/python` into the system interpreter and lose installed deps.
    args.python = args.python.absolute()
    checkpoint = args.run_dir / "checkpoint.ckpt"
    metrics = args.run_dir / "metrics.jsonl"
    validation_root = args.run_dir / "validation"
    validation_root.mkdir(parents=True, exist_ok=True)

    schedule = milestones(
        args.start_step, args.interval, args.end_step, args.baseline
    )
    print(f"Validation milestones: {schedule}", flush=True)
    for trigger_step in schedule:
        milestone_dir = validation_root / f"step_{trigger_step:09d}"
        expected = {"canonical"}
        if trigger_step > 0 and trigger_step % args.robust_interval == 0:
            expected.add("robust")
        done = completed_modes(milestone_dir) if milestone_dir.exists() else set()
        if expected <= done:
            print(f"Skipping completed milestone {trigger_step}.", flush=True)
            continue

        while latest_metric_step(metrics) < trigger_step:
            time.sleep(args.poll_seconds)

        snapshot = milestone_dir / "checkpoint.ckpt"
        if not snapshot.exists():
            # Intermediate milestones require a checkpoint written after their
            # threshold. At the final milestone, allow the stable final save:
            # training may exit without producing one more signature change.
            need_new = requires_new_checkpoint(trigger_step, args.end_step)
            if trigger_step == args.end_step and trigger_step > 0:
                print(
                    "Final milestone reached; allowing time for the final checkpoint save.",
                    flush=True,
                )
                time.sleep(args.final_checkpoint_grace_seconds)
            previous_signature = checkpoint_signature(checkpoint) if need_new else None
            print(
                f"Milestone {trigger_step} reached; waiting for stable checkpoint.",
                flush=True,
            )
            wait_for_stable_snapshot(
                checkpoint,
                snapshot,
                previous_signature,
                args.poll_seconds,
            )

        jobs: list[tuple[str, subprocess.Popen[str], Any]] = []
        if "canonical" in expected - done:
            wait_for_gpu(
                args.canonical_gpu,
                args.poll_seconds,
                args.gpu_memory_limit_mib,
                args.gpu_utilization_limit,
            )
            process, stream = launch_evaluator(
                args,
                snapshot,
                milestone_dir,
                trigger_step,
                "canonical",
                args.canonical_gpu,
            )
            jobs.append(("canonical", process, stream))
        if "robust" in expected - done:
            wait_for_gpu(
                args.robust_gpu,
                args.poll_seconds,
                args.gpu_memory_limit_mib,
                args.gpu_utilization_limit,
            )
            process, stream = launch_evaluator(
                args,
                snapshot,
                milestone_dir,
                trigger_step,
                "robust",
                args.robust_gpu,
            )
            jobs.append(("robust", process, stream))

        for mode, process, stream in jobs:
            code = process.wait()
            stream.close()
            if code:
                raise RuntimeError(
                    f"{mode} validation failed with exit code {code}; "
                    f"see {milestone_dir / f'{mode}.log'}"
                )
            result = json.loads((milestone_dir / f"{mode}.json").read_text())
            append_history(validation_root, result)
            print(
                f"Completed {mode} validation for milestone {trigger_step}.",
                flush=True,
            )

    print("All configured validation milestones are complete.", flush=True)


if __name__ == "__main__":
    main()
