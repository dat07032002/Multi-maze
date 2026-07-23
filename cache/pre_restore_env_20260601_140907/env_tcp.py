import base64
import json
import os
import socket
import time

import cv2
import gym
import numpy as np
from ament_index_python.packages import get_package_share_directory

from cyberrunner_dreamer import cyberrunner_layout
from cyberrunner_dreamer.path import LinearPath


def _recv_line(sock):
    data = bytearray()
    while True:
        b = sock.recv(1)
        if not b:
            raise ConnectionError("TCP bridge disconnected")
        if b == b"\n":
            return data.decode("utf-8")
        data.extend(b)


class CyberrunnerGym(gym.Env):
    def __init__(
        self,
        repeat=1,
        layout=cyberrunner_layout.cyberrunner_hard_layout,
        num_rel_path=5,
        num_wait_steps=30,
        reward_on_fail=0.0,
        reward_on_goal=0.5,
    ):
        super().__init__()

        self.observation_space = gym.spaces.Dict(
            image=gym.spaces.Box(0, 255, (64, 64, 1), np.uint8),
            states=gym.spaces.Box(-np.inf, np.inf, (4,), np.float32),
            goal=gym.spaces.Box(-np.inf, np.inf, (num_rel_path * 2,), np.float32),
            progress=gym.spaces.Box(-np.inf, np.inf, (1,), np.float32),
            log_reward=gym.spaces.Box(-np.inf, np.inf, (1,), np.float32),
        )
        self.action_space = gym.spaces.Box(-1.0, 1.0, (2,))
        self.obs = dict(self.observation_space.sample())

        self.num_rel_path = num_rel_path
        self.norm_max = np.array([10 * np.pi / 180.0, 10 * np.pi / 180.0, 0.276, 0.231])
        self.goal_norm_max = np.array(
            [0.0002 * 60 * k for k in range(1, self.num_rel_path + 1) for _ in range(2)]
        )

        self.offset = np.array([0.276, 0.231]) / 2.0
        shared = get_package_share_directory("cyberrunner_dreamer")
        self.p = LinearPath.load(os.path.join(shared, "path_0002_hard.pkl"))

        self.cheat = False
        self.cheat_threshold = int(0.057 / self.p.distance)
        self.prev_pos_path = 0
        self.num_wait_steps = num_wait_steps
        self.reward_on_fail = reward_on_fail
        self.reward_on_goal = reward_on_goal

        self.ball_detected = False
        self.max_angle_vel = float(os.environ.get("CYBERRUNNER_MAX_ANGLE_VEL", "180"))
        self.alpha_fac = float(os.environ.get("CYBERRUNNER_ALPHA_FAC", "-1.0"))
        self.beta_fac = float(os.environ.get("CYBERRUNNER_BETA_FAC", "-1.0"))
        self.max_cmd_1 = float(os.environ.get("CYBERRUNNER_MAX_CMD_1", "180"))
        self.max_cmd_2 = float(os.environ.get("CYBERRUNNER_MAX_CMD_2", "180"))
        self.action_repeat = max(1, int(os.environ.get("CYBERRUNNER_ACTION_REPEAT", "1")))

        self.last_time = 0
        self.progress = 0
        self.accum_reward = 0.0
        self.steps = 0
        self.off_path = False
        self.episodes = 0
        self.success = False

        host = os.environ.get("CYBERRUNNER_TCP_BIND", "0.0.0.0")
        port = int(os.environ.get("CYBERRUNNER_TCP_PORT", "5555"))

        print(f"[TCP ENV] Waiting for PC bridge on {host}:{port} ...")
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((host, port))
        self.server.listen(1)
        self.sock, addr = self.server.accept()
        self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        print(f"[TCP ENV] PC bridge connected from {addr}")
        print(f"[TCP ENV] Action repeat: {self.action_repeat}")

    def _request(self, obj):
        msg = json.dumps(obj, separators=(",", ":")).encode("utf-8") + b"\n"
        self.sock.sendall(msg)
        line = _recv_line(self.sock)
        return json.loads(line)

    def step(self, action):
        self.steps += 1

        if self.cheat and (self.p.num_points - self.prev_pos_path <= 200):
            action[1] = 1.0

        obs = self._step_remote(action)

        reward = self._get_reward(obs)
        done = self._get_done(obs)

        if done and not self.success:
            reward = self.reward_on_fail
        if self.success:
            reward += self.reward_on_goal

        if done or self.steps == 3000:
            if self.success:
                time.sleep(2)
            print("Reset board")
            self._reset_board()

        info = {"is_terminal": False} if self.success else {}

        now = time.time()
        step_dt = now - self.last_time
        if step_dt > (1.0 / 35.0):
            step_fps = 1.0 / step_dt if step_dt > 0.0 else 0.0
            print(f"Slower than 35fps: step_dt={step_dt * 1000.0:.1f} ms, fps={step_fps:.1f}")
        self.last_time = now

        self.accum_reward += reward if not done else 0
        obs["states"] = (obs["states"] / self.norm_max).astype(np.float32)
        obs["goal"] = (obs["goal"] / self.goal_norm_max).astype(np.float32)
        obs["progress"] = np.asarray([1 + self.prev_pos_path], dtype=np.float32)
        obs["log_reward"] = np.asarray([reward if not done else 0], dtype=np.float32)
        return obs, reward, done, info

    def reset(self):
        print("Resetting ...")
        self.episodes += 1
        print("Previous reward: {}".format(self.accum_reward))
        print("Previous episode length: {}".format(self.steps / 60.0))
        print("Episodes: {}".format(self.episodes))

        self.accum_reward = 0.0
        self.steps = 0
        self.success = False
        self.ball_detected = False

        self._send_action(np.zeros((2,)))

        count = 0
        obs = self._get_obs()
        while count < self.num_wait_steps:
            obs = self._get_obs()
            count = count + 1 if self.ball_detected else 0

        self.prev_pos_path = self.p.closest_point(obs["states"][2:4])[0]
        self.progress = 0
        self.last_time = time.time()

        obs["states"] = (obs["states"] / self.norm_max).astype(np.float32)
        obs["goal"] = (obs["goal"] / self.goal_norm_max).astype(np.float32)
        obs["progress"] = np.asarray([1 + self.prev_pos_path], dtype=np.float32)
        obs["log_reward"] = np.asarray([0], dtype=np.float32)
        return obs

    def render(self, mode="human"):
        pass

    def _step_remote(self, action):
        vel_1, vel_2 = self._action_to_command(action)

        rep = None
        for _ in range(self.action_repeat):
            while True:
                rep = self._request({
                    "cmd": "step",
                    "vel_1": vel_1,
                    "vel_2": vel_2,
                    "timeout": 0.018,
                })
                if rep.get("ok", False):
                    break
                time.sleep(0.01)

        return self._obs_from_reply(rep)

    def _obs_from_reply(self, rep):
        if not rep.get("ball", False):
            self.ball_detected = False
            states = np.array([0.0, 0.0, 0.0, 0.0], dtype=np.float32)
            image = np.zeros((64, 64, 1), dtype=np.uint8)
            rel_path = np.zeros((self.num_rel_path * 2,), dtype=np.float32)
            self.obs = {"states": states, "goal": rel_path, "image": image}
            return self.obs.copy()

        self.ball_detected = True

        states = np.array(
            [
                float(rep["alpha"]),
                float(rep["beta"]),
                float(rep["x_b"]),
                float(rep["y_b"]),
            ],
            dtype=np.float32,
        )
        states[2:] += self.offset

        img_bytes = base64.b64decode(rep["image_b64"])
        image = np.frombuffer(img_bytes, dtype=np.uint8).reshape(64, 64, 1)

        rel_path = np.asarray(
            self.p.get_rel_path(states[2:], self.num_rel_path, 60)
        ).flatten().astype(np.float32)

        states = np.nan_to_num(states, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)
        rel_path = np.nan_to_num(rel_path, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)
        image = np.nan_to_num(image, nan=0.0, posinf=0.0, neginf=0.0)
        image = np.clip(image, 0, 255).astype(np.uint8)

        self.obs = {"states": states, "goal": rel_path, "image": image}
        return self.obs.copy()

    def _send_action(self, action):
        vel_1, vel_2 = self._action_to_command(action)
        self._request({"cmd": "action", "vel_1": vel_1, "vel_2": vel_2})

    def _action_to_command(self, action):
        action = action.copy()
        action *= self.max_angle_vel
        vel_1 = float(self.alpha_fac * action[0])
        vel_2 = float(self.beta_fac * action[1])
        vel_1 = float(np.clip(vel_1, -self.max_cmd_1, self.max_cmd_1))
        vel_2 = float(np.clip(vel_2, -self.max_cmd_2, self.max_cmd_2))
        return vel_1, vel_2

    def _get_obs(self):
        while True:
            rep = self._request({"cmd": "obs"})
            if rep.get("ok", False):
                break
            time.sleep(0.01)

        if not rep.get("ball", False):
            self.ball_detected = False
            # Never send NaN to Dreamer. NaN observations can make the policy output NaN.
            states = np.array([0.0, 0.0, 0.0, 0.0], dtype=np.float32)
            image = np.zeros((64, 64, 1), dtype=np.uint8)
            rel_path = np.zeros((self.num_rel_path * 2,), dtype=np.float32)
            self.obs = {"states": states, "goal": rel_path, "image": image}
            return self.obs.copy()

        self.ball_detected = True

        states = np.array(
            [
                float(rep["alpha"]),
                float(rep["beta"]),
                float(rep["x_b"]),
                float(rep["y_b"]),
            ],
            dtype=np.float32,
        )
        states[2:] += self.offset

        img_bytes = base64.b64decode(rep["image_b64"])
        image = np.frombuffer(img_bytes, dtype=np.uint8).reshape(64, 64, 1)

        rel_path = np.asarray(
            self.p.get_rel_path(states[2:], self.num_rel_path, 60)
        ).flatten().astype(np.float32)
        # Final safety cleanup: block NaN/inf before Dreamer sees it.
        states = np.nan_to_num(states, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)
        rel_path = np.nan_to_num(rel_path, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)
        image = np.nan_to_num(image, nan=0.0, posinf=0.0, neginf=0.0).astype(np.uint8)

        # Final safety cleanup before Dreamer sees observation.
        states = np.nan_to_num(states, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)
        rel_path = np.nan_to_num(rel_path, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)
        image = np.nan_to_num(image, nan=0.0, posinf=0.0, neginf=0.0)
        image = np.clip(image, 0, 255).astype(np.uint8)

        self.obs = {"states": states, "goal": rel_path, "image": image}
        return self.obs.copy()

    def _get_reward(self, obs):
        if not self.ball_detected:
            reward = 0.0
        else:
            curr_pos_path, p = self.p.closest_point(obs["states"][2:4])
            self.off_path = curr_pos_path == -1
            if self.off_path and self.cheat:
                curr_pos_path = self.prev_pos_path
            self.progress = curr_pos_path - self.prev_pos_path
            reward = float(curr_pos_path - self.prev_pos_path) * 0.004 / 16.0
            self.prev_pos_path = curr_pos_path
        return reward

    def _get_done(self, obs):
        done = not self.ball_detected

        if (not self.cheat) and self.off_path:
            done = True
            print("[Done]: OFFPATH")

        if self.p.num_points - self.prev_pos_path <= 1:
            self.success = True
            done = True
            print("[Done]: SUCCESS")
            self._send_action(np.array([0.0, 0.0]))

        if (not self.cheat) and self.progress > self.cheat_threshold:
            done = True
            print("[Done]: Too high progress")

        return done

    def _reset_board(self):
        self._request({"cmd": "reset"})
