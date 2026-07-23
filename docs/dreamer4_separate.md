# Separate Dreamer4 Path

This project keeps the existing `dreamerv3/` folder and DreamerV3 console
commands unchanged. Dreamer4 should live in a separate checkout or environment.

## Commands

Rebuild the ROS Python entry points after these files change:

```bash
colcon build --symlink-install --packages-select cyberrunner_dreamer cyberrunner_dreamer_thomas
source install/setup.bash
```

Run the original DreamerV3 path exactly as before:

```bash
ros2 run cyberrunner_dreamer train
ros2 run cyberrunner_dreamer_thomas train_tcp_thomas
```

Run the separate Dreamer4 path:

```bash
export PYTHONPATH=/path/to/dreamer4:$PYTHONPATH
export CYBERRUNNER_DREAMER4_ENTRY=dreamer4.train:main
ros2 run cyberrunner_dreamer train_dreamer4
```

For the Thomas TCP package:

```bash
export PYTHONPATH=/path/to/dreamer4:$PYTHONPATH
export CYBERRUNNER_DREAMER4_ENTRY=dreamer4.train:main
ros2 run cyberrunner_dreamer_thomas train_tcp_dreamer4_thomas
```

On the training server, this repo also provides helper scripts:

```bash
./scripts/check_dreamer4_server.sh
./scripts/run_server_dreamer4_gpu12_thomas.sh
```

The GPU 1/2 script sets `CUDA_VISIBLE_DEVICES=1,2`, then maps Dreamer/JAX
devices as policy device `0` and train devices `0 1`.

If the upstream Dreamer4 entry point is named differently, only change
`CYBERRUNNER_DREAMER4_ENTRY`; do not edit the old DreamerV3 launcher.

## Nicklas Hansen Dreamer4

The `nicklashansen/dreamer4` repo is set up separately on the server at
`~/dreamer4` in its own `micromamba` environment named `dreamer4`. It is an
offline/world-model codebase with `train_tokenizer.py` and `train_dynamics.py`,
not a drop-in live Gym/RL trainer.

Check the separate environment:

```bash
cd ~/cyberruner-main
./scripts/check_nicklas_dreamer4_server.sh
```

Train the tokenizer on GPU 1 and 2 after setting preprocessed shard dirs:

```bash
export DREAMER4_TOKENIZER_DATA_DIRS="/path/to/thomas-shards"
./scripts/run_nicklas_dreamer4_tokenizer_gpu12.sh
```

Train dynamics on GPU 1 and 2 after setting raw and preprocessed dirs:

```bash
export DREAMER4_DYNAMICS_RAW_DIRS="/path/to/thomas-raw"
export DREAMER4_DYNAMICS_FRAME_DIRS="/path/to/thomas-shards"
export DREAMER4_TOKENIZER_CKPT="$HOME/dreamer4/dreamer4/logs/tokenizer_ckpts/latest.pt"
./scripts/run_nicklas_dreamer4_dynamics_gpu12.sh
```
