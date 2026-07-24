"""ROS interface profiles for organized TAG and the working legacy hardware."""

from __future__ import annotations

from dataclasses import dataclass
import importlib


@dataclass(frozen=True)
class InterfaceProfile:
    """Names and message classes used by one compatible ROS graph."""

    name: str
    camera_topic: str
    state_topic: str
    command_topic: str
    expected_driver_node: str
    state_module: str
    state_class: str
    command_module: str
    command_class: str


PROFILES = {
    "tag": InterfaceProfile(
        name="tag",
        camera_topic="/tag_camera/image",
        state_topic="/tag_state_estimation/estimate",
        command_topic="/tag_hiwonder/cmd",
        expected_driver_node="tag_hiwonder_compat",
        state_module="tag_interfaces.msg",
        state_class="StateEstimate",
        command_module="tag_interfaces.msg",
        command_class="HiwonderVel",
    ),
    "legacy-hardware": InterfaceProfile(
        name="legacy-hardware",
        camera_topic="/cyberrunner_camera/image",
        state_topic="/cyberrunner_state_estimation/estimate",
        command_topic="/cyberrunner_dynamixel/cmd",
        expected_driver_node="cyberrunner_hiwonder_compat",
        state_module="cyberrunner_interfaces.msg",
        state_class="StateEstimate",
        command_module="cyberrunner_interfaces.msg",
        command_class="DynamixelVel",
    ),
}


def get_profile(name: str) -> InterfaceProfile:
    """Return a known interface profile or raise a useful error."""

    try:
        return PROFILES[name]
    except KeyError as exc:
        choices = ", ".join(sorted(PROFILES))
        raise ValueError(f"unknown interface profile {name!r}; choose {choices}") from exc


def load_message_types(profile: InterfaceProfile):
    """Load ROS messages lazily so dry runs require no ROS workspace."""

    state_module = importlib.import_module(profile.state_module)
    command_module = importlib.import_module(profile.command_module)
    return (
        getattr(state_module, profile.state_class),
        getattr(command_module, profile.command_class),
    )
