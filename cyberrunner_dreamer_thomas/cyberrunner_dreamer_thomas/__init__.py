from gym.envs.registration import register


register(
    id="cyberrunner-thomas-ros-v0",
    entry_point="cyberrunner_dreamer_thomas.env:CyberrunnerGym",
    # max_episode_steps=6000,
)

register(
    id="cyberrunner-thomas-tcp-v0",
    entry_point="cyberrunner_dreamer_thomas.env_tcp:CyberrunnerGym",
    # max_episode_steps=6000,
)

# register(
#    id='cyberrunner-ros-v1',
#    entry_point='cyberrunner_dreamer_thomas.env:CyberrunnerGymV2',
#    #max_episode_steps=6000,
# )
