# Change log

This is a research log, not release notes. `Unreleased` is a single running
section in reverse chronological order, newest entry first, and it records
measurements and rejected hypotheses alongside shipped changes. That is
deliberate: knowing which four ideas were tested and failed is worth more here
than knowing which version a change landed in.

Because of that, it does not answer "what is true now". For current state read,
in order: [README.md](README.md) for the active experiment,
[docs/README.md](docs/README.md) for the documentation index, and
[docs/HANDOFF.md](docs/HANDOFF.md) for where the last session stopped.

## Unreleased

- Declared `log_off_route` in the tag_sim_v2 `log_keys_mean` whitelist and added
  a test that every `log_` observation the environment emits is matched by a
  logging rule. An unlisted key is dropped silently, with no error and no
  warning, so `log_off_route` reached both observation spaces and the
  environment step and still never appeared in a single row of a 50k run.
  Nothing else in the suite would have caught it, and the same trap already
  cost a round trip once before.
- Gated route progress on a measured corridor. `PolylineRoute.project` returns
  the nearest route point inside the along-route window and reports the
  cross-track distance but never used it to reject the match, so a ball nowhere
  near the route still advanced `progress_m`, ratcheted `route_completion` to
  1.0, and was paid progress reward for travel that never happened. A ball
  parked 109 mm off a 145 mm route for a whole episode scored a perfect route
  before this change and scores zero after it. `TaskConfig.progress_corridor_m`
  defaults to 40 mm, the median on-route ball clearance measured over 40
  foundation layouts, where the 1st percentile is 23.5 mm; set it to infinity to
  restore the old behavior. Episodes now report `log_off_route`.
- Made the master-course gate refuse to read route progress as evidence of
  tracking when an episode's mean cross-track error exceeds the same corridor.
  The 50k foundation validation reported `max_route_completion` of exactly 1.0
  on four layouts while averaging 174 mm of cross-track error on a 259 mm board.
  Note the corridor gate alone does not make `max_route_completion` bulletproof:
  a ball that repeatedly dips into the corridor can still ratchet, which is why
  the gate cross-check exists as a second layer.
- Recorded that `mean_max_route_completion` was therefore not a route-following
  measure whenever cross-track error was large. Historical results where the
  policy genuinely tracked the route are unaffected, because the projection is
  honest for an on-route ball; the metric only misreports off-route episodes.
- Bounded `path_tracking_cost` to [0, 1], matching `hole_proximity_cost` and
  `wall_riding_cost`. Unclipped it dominated the whole reward: the 150k
  foundation run logged a mean cost of 27.5 per step, which at the shipped
  0.002 coefficient charged about -165 per episode against a positive budget
  of 35, so standing still outscored driving. That is the frozen,
  never-completing, never-falling policy the stage produced.
- Added a trend check to the master-course gate. A stage that ends worse than
  the checkpoint it started from is no longer promotable regardless of how it
  scores against the static floors, and the gate now reports which checkpoint
  actually scored best. Plateauing at or above the floors remains promotable,
  since that means the skill is learned rather than stalled.
- Marked `tag_sim_v2_safe_path_tracking`'s `path_tracking_penalty` of 0.20 as
  uncalibrated rather than silently retuning a retired profile. Bounded, it can
  still charge 600 against a budget of 20.
- Moved the gate retention tolerances into `tag_mujoco/gate_criteria.py`. The
  0.02/0.01 pair had been copied into two gates and diverged to 0.05 in a third
  with no explanation; the master course's looser value is now documented as a
  decision.
- Fixed `TensorBoardOutput.close` raising `AttributeError` on any local-logdir
  run. Latent rather than live: the tagmaze profiles set `tensorboard: False`,
  but the default in `configs.yaml` is `True`, so it was one flag away.
- Replaced the hard failure on an unaligned vectorized step budget with a
  warning. Resuming under a different `envs.amount` is documented in
  `scripts/run_tag_v2_gpu2.sh` and routinely leaves a remainder; the final chunk
  now overshoots by less than one batch instead of refusing to launch.
- Stopped periodic replay saves from fragmenting the buffer into near-empty
  chunks. An explicit `save(wait=True)`, which is what end-of-training uses,
  still writes every partial chunk.
- Made resource cleanup resilient: one failing `close()` no longer strands the
  remaining thread pools, `train_eval` no longer leaks its first replay if the
  second fails to construct, and `os._exit` now flushes stdout so redirected
  console logs keep their tail.
- Guarded `TAG_CANONICAL_GPU` and `TAG_ROBUST_GPU` in the master-course stage
  launcher against physical GPU 0 and against sharing a device with training.
- Raised the gated master-course production ceilings to 4.5 million aggregate
  transitions: 500k foundation, 750k turns, 750k recovery, 1M hazards, and
  1.5M compound; foundation remains scratch-only and every later stage remains
  conditional on accepting the preceding stage checkpoint.
- Made master-course validation monitors barrier-aware so each fixed checkpoint
  is evaluated and explicitly released before training resumes.
- Made vectorized training budgets exact by collecting environment-count-aligned
  chunks instead of whole synchronized episodes, recording the final counter,
  and explicitly draining checkpoint, replay, and metric-writer thread pools so
  completed runs exit without manual termination.
- Added the guarded v5 multi-skill master-course curriculum: five cumulative,
  procedurally varied course families; rounded and clearance-validated routes;
  disjoint hashed train/validation/test manifests; close hazards; narrow
  corridors; controlled recovery resets; and manifest-only skill-zone labels.
- Added completion-positive training profiles with no action-rate penalty,
  strict scratch/warm-start lineage checks, fixed-step validation launching,
  and a per-family competence/retention promotion gate.
- Added nested 16/32/64/128/512 no-hole map groups with balanced initial route
  directions, uniform repeated sampling, true-entrance starts, guarded
  agent-only stage transitions, and per-stage mastery validation.
- Changed paired Phase 1 to full-start-only scratch training. Every episode now
  begins at the true maze entrance; random and near-goal curriculum starts are
  disabled after the first run exposed a severe train/evaluation mismatch.
- Added a reproducible paired 512/64/64 curriculum that learns on no-hole
  layouts first, consolidates full-start navigation, then warm-starts through
  branch holes, one easy dodge hole, and mixed holes while preserving topology.
- Added five float32, no-domain-randomization profiles, guarded phase launchers,
  retained-replay checkpoint contracts, and 192-episode mastery/retention gates.
- Reworked mature-policy continuation to load learned checkpoint variables
  before replay prefill, use the loaded policy instead of random actions, and
  reset model/actor/critic optimizer state for a genuine weights-only resume.
- Added `tag_sim_v2_nominal_safe_resume`: a 50k warm replay made from up to 25k
  source-replay transitions spread across the prior run plus new source-policy
  experience, train ratio 8, 10x lower actor/critic learning rates, lower model
  learning rate, optimizer warmup, and a separate 100k update budget.
- Changed the hole-aware continuation monitor to evaluate 192 dev episodes at
  baseline and every 25k steps, request an early stop when completion decreases
  while falls increase, and confirm the best monitored checkpoint rather than
  the final checkpoint.
- Diagnosed the completed 500k nominal pilot: the 192-episode mastery gate fails
  every criterion, seven validation layouts never succeed on any seed and cap
  completion at 89.1%, and every one of those layouts fails at a route turn in
  its own 95th percentile or above while hole and wall clearance there is normal.
- Measured that the policy drives bang-bang, averaging 0.88 to 0.93 of full
  action range with 64% to 74% of steps saturated, which cannot decelerate into a
  near-right-angle corner.
- Passed the 192-episode nominal mastery gate on the held-out validation split
  with the hole-margin arm: 90.10% completion, 6.25% falls, 95.57% mean maximum
  route completion, 88.89% hard-maze completion, and no difficulty band below
  88.89%. Recorded through `nominal_training_gate.py`.
- Removed the structural ceiling: no validation layout now fails all three
  evaluation seeds, where the pilot had seven such layouts capping completion at
  89.1%. Layout 20025, whose ball previously froze for 2,500 steps on every seed,
  now completes on two of three.
- Noted that gate completion passed by a single episode, 173 of 192, so a second
  confirmation at different evaluation seeds is required before domain
  randomization is unlocked.
- Added a dense hole-margin reward term, `hole_clearance_penalty`, defaulting to
  zero, built on a new hole-only `signed_hole_clearance`. The pre-existing
  `clearance_cost` mixes walls with holes and ordinary corridor travel sits inside
  its band, so charging it would have penalized driving down a corridor.
- Measured the hole warning band rather than guessing it: on-route hole clearance
  has a median of 18.4 mm and a 1st percentile of 8.0 mm, so an 8 mm band charges
  0.94% of on-route travel where a 12 mm band would charge 15.31%.
- Measured that the hole-margin term is the effective lever. On the dev split at
  500k it reaches 90.63% completion, 7.81% falls and 95.01% mean maximum route
  completion, against 81.25%, 18.75% and 89.11% for the matched no-penalty
  control, cutting the fall rate by more than half.
- Measured that the action-rate term reduces chatter by about 35% but does not by
  itself improve completion or progress beyond noise.
- Recorded that the no-penalty control raises completion while making falls worse,
  15.63% to 18.75%, so training longer without a hazard signal trades falls for
  progress.
- Added an `action_rate_penalty` reward term, defaulting to zero, with a shipped
  arm at 0.003 calibrated to about 6% of the episode return and a test guarding
  that budget against penalties that would reward standing still.
- Recorded that the route corners are dynamically trackable after all: at the 10
  degree board limit the minimum turn radius is 0.21 to 3.47 mm and the stopping
  distance 0.22 to 1.74 mm across observed speeds, so no maze dataset was
  regenerated and the failures are a control deficiency.
- Recorded that the corner-geometry correlation is weak at population scale, 10.3
  against 11.4 mm over 86 failing and 426 solved training layouts, so the earlier
  seven-layout figures were inflated by sample size.
- Swept all 512 training layouts and recorded the 86 the policy still fails, for
  demonstration targeting, noting that training completion of 83.20% against
  unseen 79.17% indicates an unlearned skill rather than overfitting.
- Allowed bounded A/B arms to run concurrently through `TAG_TRAIN_GPU`,
  `TAG_CANONICAL_GPU` and `TAG_ROBUST_GPU`, restricting training to physical GPU 2
  or 1, keeping physical GPU 0 unreachable, and refusing to let training share a
  device with its own validation.
- Added an `eval_mode` policy branch and an evaluator `--policy-mode` flag, and
  recorded the protocol in every result. Measured that acting on the action
  distribution mode is worse than sampling, so sampling remains the default.
- Added a deterministic 64-layout `dev` subset of the training layouts, matched
  to the validation split's difficulty bands, so tuning arms are ranked without
  reading the split that decides the mastery gate.
- Added bounded nominal A/B arms for action smoothness, gradient ratio, fall
  penalty, and prioritized-replay sharpening, plus a launcher that refuses
  non-nominal profiles and verifies randomization is disabled in the written
  config.
- Added a trajectory probe that records per-step ball position, commanded tilt,
  progress, and clearance for one deterministic held-out rollout.
- Allowed the validation monitor and evaluator to target the `dev` and `train`
  splits and to select the action protocol and canonical episode count.

- Added a nominal-first full-route DreamerV3 continuation profile that disables
  plant randomization, requires agent-only checkpoint loading, and starts with
  fresh nominal replay.
- Added a bounded 500k nominal pilot launcher with canonical validation at 250k
  and 500k, independent of the incomplete PLA demonstration dataset.
- Added separate bounded-continuation and 192-episode nominal-mastery gates so
  a single favorable validation cannot unlock domain randomization.
- Propagated camera source timestamps through `StateEstimate`, passive logs,
  and active sysid logs so actuator timing and state latency use image time
  instead of ROS receipt time when the interface provides it.
- Reworked the calibrated camera path for `1920 x 1200` capture and `640 x 400`
  output, with a low-latency GStreamer backend and an OpenCV fallback.
- Replaced frame-to-frame marble velocity differences with a timestamp-aware
  sliding linear fit, including loss resets and a configurable stationary
  deadband.
- Strengthened plate-pose validation with per-branch PnP reprojection error,
  explicit rejection diagnostics, and multi-frame recovery after a pose jump.
- Hardened hybrid marble tracking so AI-only proposals cannot initialize or
  reacquire a track; added cross-validated fusion, failure-window capture, and
  an offline presence/center labeler for hard-negative collection.
- Documented the camera-only vision reliability plan, dataset split rules, and
  acceptance gates required before another active hardware test.
- Completed guarded axis-2 and repeated command-80 actuator measurements with
  source-timestamped timing, raw-artifact hashes, and direction-dependent 2x2
  local command-to-angle maps.
- Updated the simulator and privileged route expert to use the measured
  directional actuator maps, local stiction priors, 33 ms total delay, and an
  86 ms response time constant while retaining domain randomization for
  unmeasured backlash, saturation, and stalls.
- Added approval-gated marble pulse and breakaway protocols with visibility,
  start-speed, board-boundary, speed, dropout, and confirmed-displacement
  interlocks.
- Added passive real-trajectory dynamics fitting and a quality-gated simulator
  override for tilt response, linear damping, rolling resistance, and wall
  restitution.
- Marked the user-confirmed ball radius and maze wall/hole dimensions as
  measured in the hardware parameter registry.
- Added compatibility with both common Python HID APIs and made camera,
  estimator, and recorder shutdown paths tolerate operator interrupts cleanly.
- Added a bounded plate-pose continuity gate that resets corner tracking after
  impossible PnP branches and fails non-finite after two held frames.
- Added a mixed sysid profile for the clean filtered estimator with the working
  legacy camera and Hiwonder command interfaces.
- Synchronized `tag_state_estimation/markers.csv` to the active hardware
  estimator after detecting stale organized coordinates during commissioning.
- Recorded and documented the first accepted guarded physical Hiwonder axis/sign
  run at +/-20, including local gains, coupling, timing, home repeatability, and
  raw-artifact hashes.
- Recorded and documented an accepted 40-transition Hiwonder step-response run at
  +/-10 and a safely rejected delayed stick-slip transition at +20.
- Added an explicitly selected `legacy-hardware` sysid profile so guarded passive
  and active measurements can use the working CyberRunner ROS message types and
  topics without replacing its camera, estimator, or Hiwonder driver.
- Added active-sysid runtime aborts for excessive estimated board angle and a
  stale estimator stream.
- Added a median preflight angle baseline and a separately bounded excursion
  limit so estimator zero offsets cannot disable motion safety.
- Added a hard-bounded active-protocol command scale for safely reducing all
  excitation amplitudes after reviewing an initial response.
- Added a sanitized read-only audit of the live hardware and training systems,
  including machine-readable runtime and DreamerV3 snapshots.
- Documented the 240-to-180 action clamp, legacy-to-`tag_*` topic remapping,
  estimator provenance, missing image timestamp, stopped hardware run, and P0
  deployment gates.
- Added the passive `tag_sysid` recorder and offline analyzer.
- Added guarded home, axis/sign, static-sweep, and step-response protocols.
- Added hard bounds, publisher exclusivity, explicit arming, raw CSV output,
  home fallback, and protocol/safety/analysis tests.
- Imported the working TAG hardware stack through upstream commit `35b80ad`.
- Added a hardware-compatible DreamerV3 observation/action contract.
- Added one-policy multi-maze MuJoCo training with immutable 40/8/8 splits.
- Added route-conditioned validation on physical GPUs 3 and 4 while training uses GPU 2.
- Added detector-loss recovery, Hiwonder timing/safety behavior, and domain randomization.
- Added a single-source maze route/MJCF/preview/prototype-STL exporter.
- Confirmed that the `259 x 229 mm` printed footprint fits the removable board.
- Made maze hashes portable between Windows and Linux checkouts.
- Replaced duplicated legacy packages and tracked build products with the updated `tag_*` source tree.
- Removed Dreamer4, Dynamixel/Feetech, generic benchmark, and obsolete generated artifacts.

## v0.1.0 (2024-10-21)

Initial upstream CyberRunner release.
