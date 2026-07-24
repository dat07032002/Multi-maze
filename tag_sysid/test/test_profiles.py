import unittest

from tag_sysid.profiles import PROFILES, get_profile


class InterfaceProfileTest(unittest.TestCase):
    def test_tag_profile_uses_organized_interfaces(self):
        profile = get_profile("tag")
        self.assertEqual(profile.command_class, "HiwonderVel")
        self.assertEqual(profile.command_topic, "/tag_hiwonder/cmd")
        self.assertEqual(profile.expected_driver_node, "tag_hiwonder_compat")

    def test_legacy_profile_matches_working_hardware_graph(self):
        profile = get_profile("legacy-hardware")
        self.assertEqual(profile.command_class, "DynamixelVel")
        self.assertEqual(
            profile.command_topic, "/cyberrunner_dynamixel/cmd"
        )
        self.assertEqual(
            profile.state_topic, "/cyberrunner_state_estimation/estimate"
        )
        self.assertEqual(
            profile.expected_driver_node, "cyberrunner_hiwonder_compat"
        )

    def test_all_profiles_are_absolute_and_distinct(self):
        command_topics = set()
        for profile in PROFILES.values():
            self.assertTrue(profile.camera_topic.startswith("/"))
            self.assertTrue(profile.state_topic.startswith("/"))
            self.assertTrue(profile.command_topic.startswith("/"))
            command_topics.add(profile.command_topic)
        self.assertEqual(len(command_topics), len(PROFILES))

    def test_unknown_profile_is_rejected(self):
        with self.assertRaises(ValueError):
            get_profile("unknown")


if __name__ == "__main__":
    unittest.main()
