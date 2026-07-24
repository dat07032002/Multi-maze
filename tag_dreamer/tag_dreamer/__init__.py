try:
    from gym.envs.registration import register
except ModuleNotFoundError:
    # Route and layout utilities are also used by the simulator, whose local
    # environment uses Gymnasium rather than the unmaintained Gym package.
    from gymnasium.envs.registration import register


register(
    id="tag-ros-v0",
    entry_point="tag_dreamer.env_tcp:TagGym",
)

register(
    id="tag-ros-shaped-v0",
    entry_point="tag_dreamer.env_tcp_shaped:TagGym",
)
