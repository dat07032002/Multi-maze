# CyberRunner Training, Policy, Reward, and Checkpoints

This document explains how the CyberRunner training setup works in this repo, what data is collected, how DreamerV3 uses that data, how reward and score are computed, and how to choose or continue from a trained policy.

## Big Picture

CyberRunner is trained with reinforcement learning. The robot observes the board and ball, chooses motor commands, receives reward based on path progress, and improves its policy over many episodes.

In the split-run setup:

- The server runs DreamerV3 training.
- The local PC runs camera, state estimation, motor control, and `tcp_ros_bridge.py`.
- The server sends velocity commands through TCP.
- The PC applies those commands to the servos and sends observations back.

The main training environment is:

```text
cyberrunner_dreamer/cyberrunner_dreamer/env_tcp.py
```

The local ROS environment version is:

```text
cyberrunner_dreamer/cyberrunner_dreamer/env.py
```

## What Is Being Trained

The trained object is the policy. The policy is a neural network inside DreamerV3 that maps observations to actions.

In this project:

```text
observation -> policy -> action -> servo command
```

Observation includes:

- Small camera image of the ball/board: `64 x 64 x 1`
- Board angles: `alpha`, `beta`
- Ball position: `x_b`, `y_b`
- Goal/path information from the saved path file
- Progress information

Action is:

```text
action = [axis_1_command, axis_2_command]
```

Each action value comes from Dreamer in the range:

```text
-1.0 to +1.0
```

The environment scales it to motor velocity commands:

```python
self.max_angle_vel = 80
self.alpha_fac = -1.0
self.beta_fac = -1.0
```

So roughly:

```text
action 1.0  -> command around +/-80
action 0.5  -> command around +/-40
action 0.0  -> command 0
```

## What Is An Episode

An episode is one attempt at the maze.

An episode starts when the environment resets and waits until the ball is detected for enough frames.

An episode ends when:

- The ball disappears
- The ball goes off path
- The ball reaches the goal
- The episode hits the maximum step limit

When the episode ends, Dreamer logs an episode score.

## Reward And Score

Reward is based on forward progress along the path. In the environment, the reward is:

```python
reward = float(curr_pos_path - self.prev_pos_path) * 0.004 / 16.0
```

Meaning:

```text
reward = progress along path, scaled down
```

If the ball moves forward on the path, reward is positive.
If the ball does not progress, reward is small or zero.
If the ball fails early, the episode score is low.

Episode score is the sum of all rewards in one episode:

```text
episode score = reward_1 + reward_2 + reward_3 + ...
```

This is why score is not percent. For this map:

```text
score around 1.5 = about half of the map
score around 2.9 = near finish / full map
```

So if the robot reaches around 50 percent of the map and score is around `1.5`, that is normal.

## Data Collection

Training data is collected from robot interaction.

Every step contains something like:

```text
observation
action
reward
done flag
```

Dreamer stores this in replay data:

```text
~/cyberrunner_logs/RUN_NAME/replay/
```

The replay folder contains many `.npz` files. These are chunks of experience.

Dreamer trains from replay by sampling many past sequences. This lets it learn from previous attempts, not only the current episode.

## What DreamerV3 Does

DreamerV3 is a model-based reinforcement learning algorithm.

The simple version:

1. It collects real robot experience.
2. It learns a world model from that experience.
3. The world model predicts what may happen after actions.
4. The policy improves by imagining future outcomes inside the learned model.
5. The improved policy is used on the real robot to collect more experience.

So Dreamer does not only learn directly from immediate reward. It also learns a predictive model of:

```text
current observation + action -> future latent state/reward
```

Then it trains the policy to choose actions that should lead to higher future reward.

## Why This Is Reinforcement Learning

This is reinforcement learning because:

- The system is not given examples like "when image looks like this, use command 37".
- The system tries actions.
- It receives reward.
- It updates the policy to get more reward in the future.

The goal is:

```text
maximize expected episode score
```

For CyberRunner, that means:

```text
move the ball farther along the path and finish the maze reliably
```

## Checkpoints

The trained policy is saved in checkpoint files.

Normal training saves:

```text
~/cyberrunner_logs/RUN_NAME/checkpoint.ckpt
```

This is the latest checkpoint. It is not always the best checkpoint.

If training gets worse near the end, the latest checkpoint may be worse than an earlier policy.

## Why Latest Is Not Always Best

From your `robust_2` score history, there were examples like:

```text
best score around 2.93
last score around 0.02
```

That means the policy had good episodes earlier, but the latest saved checkpoint may not represent the best behavior.

This can happen because:

- Training still explores.
- A good episode can be followed by bad episodes.
- The model can overfit or drift.
- The robot/camera conditions can vary.
- The latest checkpoint overwrites older checkpoints.

## Normal Training

Normal training uses:

```bash
--run.script train
```

This keeps the original Dreamer behavior:

```text
checkpoint.ckpt = latest policy
```

Run shape:

```bash
python3 -m dreamerv3.train \
  --configs cyberrunner large \
  --task gym_cyberrunner_dreamer:cyberrunner-ros-v0 \
  --logdir ~/cyberrunner_logs/RUN_NAME \
  --replay_size 1e6 \
  --run.script train \
  --run.train_ratio 128 \
  --run.save_every 20 \
  --run.log_every 10 \
  --jax.policy_devices 0 \
  --jax.train_devices 0
```

## Training From An Old Checkpoint

To start from an old policy:

```bash
--run.from_checkpoint ~/cyberrunner_logs/OLD_RUN/checkpoint.ckpt
```

Example:

```bash
python3 -m dreamerv3.train \
  --configs cyberrunner large \
  --task gym_cyberrunner_dreamer:cyberrunner-ros-v0 \
  --logdir ~/cyberrunner_logs/NEW_RUN \
  --run.from_checkpoint ~/cyberrunner_logs/robust_2/checkpoint.ckpt \
  --replay_size 1e6 \
  --run.script train \
  --run.train_ratio 128 \
  --run.save_every 20 \
  --run.log_every 10 \
  --jax.policy_devices 0 \
  --jax.train_devices 0
```

Important: if the old checkpoint does not contain replay, the policy can load but replay still needs to be filled. That is why the new scripts below use the loaded policy during prefill instead of a random policy.

## Train Best

We added a separate script:

```text
dreamerv3/dreamerv3/embodied/run/train_best.py
```

Use it with:

```bash
--run.script train_best
```

It saves:

```text
checkpoint.ckpt
checkpoint_best.ckpt
checkpoint_best_score.txt
```

How it works:

```text
after each episode:
    compute episode score
    if score is higher than best score so far:
        save checkpoint_best.ckpt
```

This does not automatically keep training from the best checkpoint inside the same run. It keeps training normally, but saves the best policy as a backup.

To continue from the best policy later:

```bash
--run.from_checkpoint ~/cyberrunner_logs/RUN_NAME/checkpoint_best.ckpt
```

## Train Top 5

We also added another separate script:

```text
dreamerv3/dreamerv3/embodied/run/train_top5.py
```

Use it with:

```bash
--run.script train_top5
```

It saves up to 5 top checkpoints:

```text
checkpoint_top_score2.930750_step1340865_episode123.ckpt
checkpoint_top_score2.928000_step1163023_episode99.ckpt
...
checkpoint_top5.txt
checkpoint_top5.json
```

How it works:

```text
after each episode:
    compute episode score
    if score is in top 5 so far:
        save a checkpoint
        remove checkpoint files that are no longer top 5
        update checkpoint_top5.txt
```

This is safer than saving only one best checkpoint because one high-score episode can happen by luck. With top 5, you can evaluate several candidates and choose the most reliable.

Run command:

```bash
cd /home/tbt589/cyberruner-main
source install/setup.bash

RUN=from_robust2_top5_$(date +%Y%m%d_%H%M%S)

python3 -m dreamerv3.train \
  --configs cyberrunner large \
  --task gym_cyberrunner_dreamer:cyberrunner-ros-v0 \
  --logdir ~/cyberrunner_logs/$RUN \
  --run.from_checkpoint ~/cyberrunner_logs/robust_2/checkpoint.ckpt \
  --replay_size 1e6 \
  --run.script train_top5 \
  --run.train_ratio 128 \
  --run.save_every 20 \
  --run.log_every 10 \
  --jax.policy_devices 0 \
  --jax.train_devices 0
```

Check the ranking:

```bash
cat ~/cyberrunner_logs/$RUN/checkpoint_top5.txt
```

Use one of the top checkpoints:

```bash
--run.from_checkpoint ~/cyberrunner_logs/$RUN/CHECKPOINT_FILENAME.ckpt
```

## Evaluation

Evaluation means testing a policy without training it.

Training mode:

```text
learns + explores + updates policy
```

Eval mode:

```text
uses checkpoint only, no learning
```

Eval command:

```bash
python3 -m dreamerv3.train \
  --configs cyberrunner large \
  --task gym_cyberrunner_dreamer:cyberrunner-ros-v0 \
  --logdir ~/cyberrunner_logs/eval_RUN_$(date +%Y%m%d_%H%M%S) \
  --run.from_checkpoint ~/cyberrunner_logs/RUN_NAME/checkpoint.ckpt \
  --run.steps 10000 \
  --run.script eval_only \
  --jax.policy_devices 0 \
  --jax.train_devices 0
```

For top-5 checkpoints, evaluate each one and pick the one with the best success rate, not only the highest single episode score.

## What Makes This Hard

CyberRunner is difficult because the system is real-time and physical.

Main difficulties:

- Camera noise
- Ball detection loss
- Board angle estimation noise
- Servo delay and acceleration limits
- Slight differences between motor types
- Fast dynamics of the ball
- Sparse success: finishing the maze is hard
- Exploration can cause failure
- A high score can happen by luck
- Latest checkpoint can be worse than an earlier checkpoint

The policy must learn both:

```text
how to move forward
```

and:

```text
how to recover from bad positions
```

Recovery is often harder than normal forward movement.

## Practical Workflow

Recommended workflow:

1. Start from a known checkpoint, for example `robust_2/checkpoint.ckpt`.
2. Train with `train_top5`.
3. Let it collect several top checkpoints.
4. Evaluate each top checkpoint.
5. Pick the most reliable one.
6. Start the next training run from that checkpoint.

Example sequence:

```text
robust_2/checkpoint.ckpt
    -> train_top5
    -> checkpoint_top_score...
    -> eval each top checkpoint
    -> choose best reliable checkpoint
    -> train_top5 again from that checkpoint
```

This is better than blindly continuing from the latest checkpoint.

## Useful Files

Environment:

```text
cyberrunner_dreamer/cyberrunner_dreamer/env_tcp.py
cyberrunner_dreamer/cyberrunner_dreamer/env.py
```

Training launcher:

```text
dreamerv3/dreamerv3/train.py
```

Normal train:

```text
dreamerv3/dreamerv3/embodied/run/train.py
```

Best checkpoint train:

```text
dreamerv3/dreamerv3/embodied/run/train_best.py
```

Top-5 checkpoint train:

```text
dreamerv3/dreamerv3/embodied/run/train_top5.py
```

Logs:

```text
~/cyberrunner_logs/RUN_NAME/
```

Important log files:

```text
scores.jsonl
metrics.jsonl
checkpoint.ckpt
checkpoint_best.ckpt
checkpoint_top5.txt
checkpoint_top5.json
replay/
```

## Short Summary

- The policy is the neural network that chooses servo commands.
- Reward is based on path progress.
- Episode score is the sum of rewards.
- Data is collected from real robot interaction and stored in replay.
- DreamerV3 learns a world model and trains the policy using imagined futures.
- Normal `checkpoint.ckpt` is latest, not always best.
- `train_best` saves the single best checkpoint.
- `train_top5` saves the top 5 checkpoints.
- The safest workflow is to train top 5, evaluate them, and continue from the most reliable checkpoint.
