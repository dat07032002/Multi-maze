"""Immutable policy identities and conservative champion promotion gates."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Any, Mapping

from .recording import file_sha256


@dataclass(frozen=True)
class PromotionGateConfig:
    """Conservative thresholds for replacing an immutable champion."""

    minimum_episodes: int = 64
    maximum_completion_regression: float = 0.01
    maximum_fall_regression: float = 0.0
    maximum_hard_completion_regression: float = 0.02
    required_overall_completion_gain: float = 0.01
    required_target_completion_gain: float = 0.03
    required_fall_reduction: float = 0.01
    maximum_intervention_regression: float = 0.0


class PromotionGate:
    """Compare matched champion and candidate evaluation summaries."""

    def __init__(self, config: PromotionGateConfig = PromotionGateConfig()):
        """Create a gate using immutable comparison thresholds."""
        self.config = config

    def evaluate(
        self,
        champion: Mapping[str, Any],
        candidate: Mapping[str, Any],
        *,
        champion_target: Mapping[str, Any] | None = None,
        candidate_target: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Return a machine-readable pass decision and all failure reasons."""
        config = self.config
        reasons: list[str] = []
        if int(champion.get("episodes", 0)) < config.minimum_episodes:
            reasons.append("insufficient_champion_episodes")
        if int(candidate.get("episodes", 0)) < config.minimum_episodes:
            reasons.append("insufficient_candidate_episodes")
        completion_delta = float(candidate["completion_rate"]) - float(
            champion["completion_rate"]
        )
        fall_delta = float(candidate["fall_rate"]) - float(
            champion["fall_rate"]
        )
        hard_delta = float(candidate.get("hard_completion_rate", 0.0)) - float(
            champion.get("hard_completion_rate", 0.0)
        )
        if completion_delta < -config.maximum_completion_regression:
            reasons.append("overall_completion_regression")
        if fall_delta > config.maximum_fall_regression:
            reasons.append("fall_rate_regression")
        if hard_delta < -config.maximum_hard_completion_regression:
            reasons.append("hard_completion_regression")
        intervention_delta = None
        if (
            "interventions_per_episode" in champion
            and "interventions_per_episode" in candidate
        ):
            intervention_delta = float(
                candidate["interventions_per_episode"]
            ) - float(champion["interventions_per_episode"])
            if intervention_delta > config.maximum_intervention_regression:
                reasons.append("intervention_rate_regression")

        target_delta = None
        if champion_target is not None and candidate_target is not None:
            target_delta = float(candidate_target["completion_rate"]) - float(
                champion_target["completion_rate"]
            )
        improved = (
            completion_delta >= config.required_overall_completion_gain
            or -fall_delta >= config.required_fall_reduction
            or (
                target_delta is not None
                and target_delta >= config.required_target_completion_gain
            )
        )
        if not improved:
            reasons.append("no_required_improvement")
        return {
            "schema_version": 1,
            "passed": not reasons,
            "reasons": reasons,
            "deltas": {
                "completion_rate": completion_delta,
                "fall_rate": fall_delta,
                "hard_completion_rate": hard_delta,
                "target_completion_rate": target_delta,
                "interventions_per_episode": intervention_delta,
            },
        }


def evaluation_summary(result: Mapping[str, Any]) -> dict[str, Any]:
    """Accept either a direct summary or an eval_multimaze result."""
    if "summary" not in result:
        return dict(result)
    summary = dict(result["summary"])
    hard = result.get("by_difficulty", {}).get("hard", {})
    if hard.get("completion_rate") is not None:
        summary["hard_completion_rate"] = hard["completion_rate"]
    return summary


def policy_identity(
    checkpoint: Path,
    *,
    role: str,
    parent_sha256: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a hash-bound checkpoint identity for a policy registry."""
    checkpoint = checkpoint.resolve()
    if not checkpoint.is_file():
        raise FileNotFoundError(checkpoint)
    return {
        "schema_version": 1,
        "role": role,
        "checkpoint": str(checkpoint),
        "checkpoint_sha256": file_sha256(checkpoint),
        "parent_sha256": parent_sha256,
        "metadata": dict(metadata or {}),
    }


def promote_candidate(
    registry_path: Path,
    candidate: Mapping[str, Any],
    decision: Mapping[str, Any],
    *,
    expected_champion_sha256: str,
) -> None:
    """Atomically update a registry after a reviewed passing decision."""
    if not bool(decision.get("passed", False)):
        raise ValueError("cannot promote a candidate that failed its gate")
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    champion = registry["champion"]
    if champion["checkpoint_sha256"] != expected_champion_sha256:
        raise RuntimeError("champion changed since the promotion was reviewed")
    if candidate["checkpoint_sha256"] == expected_champion_sha256:
        raise ValueError(
            "candidate and champion checkpoint hashes are identical"
        )
    history = list(registry.get("history", []))
    history.append(champion)
    updated = {
        **registry,
        "champion": dict(candidate),
        "history": history,
        "last_promotion_decision": dict(decision),
    }
    temporary = registry_path.with_suffix(registry_path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(updated, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, registry_path)
