#!/usr/bin/env bash
set -euo pipefail

project_root="$HOME/roboracer_project"
python_bin="$project_root/venv/bin/python"

echo "== venv python =="
"$python_bin" --version

echo "== installed key packages =="
"$python_bin" -m pip list --format=freeze \
  | grep -Ei '^(jax|jaxlib|mujoco|gym|gymnasium|numpy|ruamel|embodied|dreamer)=' \
  || true

echo "== imports and JAX devices, physical GPU 2 only =="
CUDA_VISIBLE_DEVICES=2 "$python_bin" - <<'PY'
import importlib

for name in ("jax", "mujoco", "gym", "gymnasium", "numpy", "ruamel.yaml"):
    try:
        module = importlib.import_module(name)
        print(name, "OK", getattr(module, "__version__", ""))
    except Exception as exc:
        print(name, "MISSING", type(exc).__name__, str(exc))

try:
    import jax
    print("jax devices", jax.devices())
except Exception as exc:
    print("jax devices ERROR", repr(exc))
PY

echo "== existing Dreamer revision =="
git -C "$project_root/phase4_learning/dreamerv3" log -1 --oneline

echo "== activate.sh =="
sed -n '1,180p' "$project_root/activate.sh"
