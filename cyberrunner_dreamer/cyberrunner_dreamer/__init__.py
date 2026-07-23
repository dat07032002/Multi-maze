from gym.envs.registration import register


register(
    id="cyberrunner-ros-v0",
    entry_point="cyberrunner_dreamer.env_tcp:CyberrunnerGym",
)

register(
    id="cyberrunner-ros-shaped-v0",
    entry_point="cyberrunner_dreamer.env_tcp_shaped:CyberrunnerGym",
)
