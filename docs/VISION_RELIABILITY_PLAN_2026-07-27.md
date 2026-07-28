# TAG marble-vision reliability plan (2026-07-27)

## Scope and safety boundary

This plan improves camera-only marble state estimation. Data capture, training,
ONNX export, and shadow evaluation do not publish motor commands. DreamerV3,
the TCP bridge, and physical policies remain stopped. Active hardware tests are
outside this plan until camera-only acceptance gates pass.

## Evidence from the current system

- The deployed model uses a `320 x 200` image and a stride-4 heatmap.
- Eighty no-motion control frames produced 80/80 detections. Relative to the
  median detected location, p95 error was `0.30 px`, maximum error was `0.38 px`,
  and confidence ranged from `0.9941` to `0.9963`.
- During board excitation, the detector sometimes retained high confidence but
  jumped more than the 25 px tracker gate while HSV simultaneously dropped out.
- Kalman prediction then drifted substantially under the measured board tilt.
  Predicted positions must therefore be explicitly distinguished from camera
  measurements in sysid and safety logs.
- The current random per-image split mixes adjacent video frames, so validation
  loss and localization error are optimistic. Synthetic negatives derived from
  a positive frame can also land in the opposite split from their source.

Conclusion: stationary appearance modeling is already strong. The dominant
failure is motion-domain shift plus uncalibrated presence confidence, not a lack
of raw model capacity.

## Research basis

1. Preserve high-resolution representations for precise heatmap localization,
   following the principle demonstrated by HRNet:
   https://openaccess.thecvf.com/content_CVPR_2019/html/Sun_Deep_High-Resolution_Representation_Learning_for_Human_Pose_Estimation_CVPR_2019_paper.html
2. Represent the marble as a center point and train a Gaussian center heatmap,
   following CenterNet's point-based formulation:
   https://arxiv.org/abs/1904.07850
3. Use focal loss and hard-negative mining so easy background pixels do not
   dominate and real distractors drive learning:
   https://openaccess.thecvf.com/content_iccv_2017/html/Lin_Focal_Loss_for_ICCV_2017_paper.html
   https://openaccess.thecvf.com/content_cvpr_2016/html/Shrivastava_Training_Region-Based_Object_CVPR_2016_paper.html
4. Add short temporal context using the previous image and previous center
   heatmap, adapted from CenterTrack's tracking-as-points design:
   https://www.ecva.net/papers/eccv_2020/papers_ECCV/html/2342_ECCV_2020_paper.php
5. Calibrate the independent presence probability on held-out sessions;
   temperature scaling is the first method to evaluate:
   https://proceedings.mlr.press/v70/guo17a.html
6. Train explicitly for blur rather than relying on generic color jitter:
   https://openaccess.thecvf.com/content/CVPR2021/html/Sayed_Improved_Handling_of_Motion_Blur_in_Online_Object_Detection_CVPR_2021_paper.html
7. Use the known planar geometry to rectify the board before inference. This is
   a deterministic version of spatial normalization; the broader learned
   transformation principle is described by Spatial Transformer Networks:
   https://papers.nips.cc/paper_files/paper/2015/hash/33ceb07bf4eeb3da587e268d663aba1a-Abstract.html

## Proposed design

### 1. Geometry-first input

- Use the accepted four-corner plate pose to warp every camera frame into a
  fixed top-down board image.
- Mask pixels outside the playable polygon.
- Keep at least 2x the current marble diameter in feature resolution. Start with
  a `512 x 416` rectified input and an output stride of 2; benchmark smaller
  variants only after accuracy is established.
- When plate pose is rejected, publish `lost_pose`; never run the detector on a
  silently stale or unrelated warp.

### 2. Compact multi-head model

- A small high-resolution encoder/decoder with lateral skip connections.
- Center heatmap head trained with Gaussian targets and focal loss.
- Independent presence head trained on real visible/absent labels.
- Optional log-variance head for localization uncertainty. Do not use heatmap
  maximum as both location and presence probability.
- Export through ONNX opset 17 and validate numerically against PyTorch.

### 3. Temporal model, only after the single-frame baseline

- Input the current rectified frame, previous rectified frame, and previous
  accepted heatmap, following the minimal CenterTrack pattern.
- Predict current center plus displacement from the previous accepted center.
- Keep the existing spatial innovation gate. A temporal model may reduce gaps;
  it may not bypass presence, board-boundary, or pose-quality gates.
- Do not add RAFT or a large generic tracker unless this compact two-frame model
  fails an ablation test; one known object on a rectified plane does not need a
  general multi-object stack.

### 4. Data and splitting

Capture separate sessions, retaining session IDs and timestamps:

- `D0`: current stationary visible controls.
- `D1`: marble manually placed throughout playable corridors, board stationary.
- `D2`: empty board, blue markers, holes, reflections, hands, and cables as true
  negatives.
- `D3`: manual camera-only board tilts, lighting changes, partial occlusion, and
  motion blur. Motors remain disabled.
- `D4`: later, guarded physical-excitation clips only after camera-only gates.

Label full short clips, not isolated favorable frames. Split by entire capture
session and condition: 70% train, 15% calibration, 15% final test. Adjacent
frames and synthetic derivatives of one source frame must stay in one split.

Augmentations should include exposure/gamma, white balance, sensor noise,
defocus, direction-and-length randomized motion blur, small pose-warp errors,
shadows, and cutout occlusion. Mine actual false positives and high-loss frames
after every training round.

## Evaluation and acceptance gates

Report metrics separately for stationary, tilt, blur, occlusion, empty-board,
and distractor sessions:

- Presence precision/recall and false positives per hour.
- Localization median, p95, and maximum pixel error.
- Board-coordinate median and p95 millimeter error.
- Rate of jumps above 12 px and 25 px.
- Dropout count, p95 duration, and maximum duration.
- Calibration error and reliability curve for presence probability.
- PyTorch/ONNX numerical agreement and robot-side inference latency.

Camera-only gate before any active sysid:

- zero false presence events on the held-out empty-board test;
- p95 visible localization error <= 2 px and maximum <= 5 px;
- no accepted jump above 12 px;
- no unreported prediction: every output is tagged measured, predicted, or lost;
- at least 30 minutes of shadow-mode validation with maximum dropout <= 100 ms;
- 60 Hz camera throughput with estimator compute below the frame period.

## Execution phases

1. Add provenance-aware capture and labeling schemas; collect D1-D3 without
   motors.
2. Build a session-grouped baseline evaluator for the current ONNX model.
3. Train and compare: current network, rectified stride-2 network, presence-head
   network, then the two-frame temporal variant.
4. Calibrate the chosen presence head on the untouched calibration sessions.
5. Export ONNX and replay every held-out clip offline.
6. Deploy in `shadow` mode only and collect 30+ minutes of diagnostics.
7. If all gates pass, propose a separate guarded physical sysid protocol.

## Server workspace

- Host: `tn22833@aere-a83514.ae.utexas.edu`
- Environment: `~/miniconda3/envs/tag-vision`
- Workspace: `~/TAG_vision_20260727`
- Use one GPU initially: `CUDA_VISIBLE_DEVICES=0`.
- Do not modify the existing `isaaclab` environment or prior TAG artifacts.
