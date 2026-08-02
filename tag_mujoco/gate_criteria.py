"""Shared promotion-gate criteria.

Three gates gate three curricula: `curriculum_phase_gate` for the paired
no-hole-to-hole phases, `skill_curriculum_gate` for the skill-first families,
and `master_course_gate` for the cumulative master course. Each has its own
thresholds, which is intended -- the curricula ask for different things -- but
the retention tolerances were copied between them and then drifted apart
without comment. Naming them in one place makes a divergence a decision rather
than an accident.
"""

from __future__ import annotations


# A warm-started phase or skill is allowed to give back this much of its
# earlier evaluation before promotion is refused. Both curricula evaluate a
# single previous stage against a directly matched baseline, so the tolerance
# only has to absorb evaluation noise.
MAXIMUM_COMPLETION_LOSS = 0.02
MAXIMUM_PROGRESS_LOSS = 0.01

# The master course is deliberately looser. It re-evaluates every earlier stage
# on every promotion, so a single tolerance is applied up to five times over a
# run, and its floors in master_course_gate.COMPLETION_FLOORS already provide
# an absolute lower bound that the phase and skill gates do not have. This is
# the reason for the difference; it is not a copy that drifted.
MASTER_COURSE_RETENTION_COMPLETION_DROP = 0.05

# A stage that ends worse than it started has not learned the skill, however it
# scores against a static floor. Anything past this drop against the stage's own
# first evaluation is treated as a regression rather than noise.
REGRESSION_TOLERANCE = 0.02

# Route completion is a projection of the ball onto the route, so it only means
# "followed the route" while the ball is near the route. Past this mean
# cross-track error an episode's reported progress is not evidence of tracking
# and must not be allowed to satisfy a progress floor. Matches
# TaskConfig.progress_corridor_m, which is where the environment stops crediting
# progress at all; an episode averaging worse than the corridor width spent most
# of itself outside it. The 50k foundation validation reported route completion
# 1.0 at a mean cross-track error of 174 mm, which is what this rejects.
MAXIMUM_TRUSTED_CROSS_TRACK_M = 0.040
