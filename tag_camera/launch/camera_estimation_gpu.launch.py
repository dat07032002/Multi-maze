from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, TimerAction
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from launch_ros.parameter_descriptions import ParameterValue
from launch.substitutions import PathJoinSubstitution


def generate_launch_description():
    device = LaunchConfiguration("device")
    gpu_backend = LaunchConfiguration("gpu_backend")
    gpu_device_id = LaunchConfiguration("gpu_device_id")
    require_gpu = LaunchConfiguration("require_gpu")
    estimator_executable = LaunchConfiguration("estimator_executable")
    ai_mode = LaunchConfiguration("ai_mode")
    ai_model_path = LaunchConfiguration("ai_model_path")

    return LaunchDescription(
        [
            DeclareLaunchArgument("device", default_value="/dev/video2"),
            DeclareLaunchArgument("gpu_backend", default_value="auto"),
            DeclareLaunchArgument("gpu_device_id", default_value="0"),
            DeclareLaunchArgument("require_gpu", default_value="false"),
            DeclareLaunchArgument("camera_fps", default_value="60.0"),
            DeclareLaunchArgument("camera_width", default_value="1280"),
            DeclareLaunchArgument("camera_height", default_value="720"),
            DeclareLaunchArgument("output_width", default_value="640"),
            DeclareLaunchArgument("output_height", default_value="360"),
            DeclareLaunchArgument("border_y", default_value="20"),
            DeclareLaunchArgument("pipeline_fps", default_value="55.0"),
            DeclareLaunchArgument("process_every_n", default_value="1"),
            DeclareLaunchArgument(
                "estimator_executable", default_value="estimator_sub"
            ),
            DeclareLaunchArgument("ai_mode", default_value="off"),
            DeclareLaunchArgument(
                "ai_model_path",
                default_value=PathJoinSubstitution(
                    [
                        FindPackageShare("tag_state_estimation"),
                        "models",
                        "marble_detector.onnx",
                    ]
                ),
            ),
            DeclareLaunchArgument("ai_backend", default_value="cpu"),
            DeclareLaunchArgument(
                "ai_confidence_threshold", default_value="0.90"
            ),
            DeclareLaunchArgument(
                "ai_check_every_n_frames", default_value="3"
            ),
            DeclareLaunchArgument("orientation_mode", default_value="camera"),
            DeclareLaunchArgument("imu_topic", default_value="/tag_imu/data"),
            DeclareLaunchArgument("imu_timeout_sec", default_value="0.10"),
            DeclareLaunchArgument(
                "imu_camera_correction_gain", default_value="0.05"
            ),
            DeclareLaunchArgument(
                "imu_max_disagreement_deg", default_value="8.0"
            ),
            DeclareLaunchArgument("imu_mount_roll_deg", default_value="0.0"),
            DeclareLaunchArgument("imu_mount_pitch_deg", default_value="0.0"),
            DeclareLaunchArgument("imu_mount_yaw_deg", default_value="0.0"),
            DeclareLaunchArgument("start_imu_serial", default_value="false"),
            DeclareLaunchArgument("imu_port", default_value="/dev/ttyACM0"),
            DeclareLaunchArgument("imu_baud", default_value="115200"),
            Node(
                package="tag_state_estimation",
                executable="bno086_serial",
                name="tag_bno086_serial",
                output="screen",
                condition=IfCondition(LaunchConfiguration("start_imu_serial")),
                parameters=[
                    {
                        "port": LaunchConfiguration("imu_port"),
                        "baud": ParameterValue(
                            LaunchConfiguration("imu_baud"), value_type=int
                        ),
                        "topic": LaunchConfiguration("imu_topic"),
                    }
                ],
            ),
            Node(
                package="tag_camera",
                executable="fast_camera_publisher.py",
                name="tag_camera",
                output="screen",
                parameters=[
                    {
                        "device": device,
                        "fps": ParameterValue(
                            LaunchConfiguration("camera_fps"), value_type=float
                        ),
                        "width": ParameterValue(
                            LaunchConfiguration("camera_width"), value_type=int
                        ),
                        "height": ParameterValue(
                            LaunchConfiguration("camera_height"),
                            value_type=int,
                        ),
                        "output_width": ParameterValue(
                            LaunchConfiguration("output_width"), value_type=int
                        ),
                        "output_height": ParameterValue(
                            LaunchConfiguration("output_height"),
                            value_type=int,
                        ),
                        "border_y": ParameterValue(
                            LaunchConfiguration("border_y"), value_type=int
                        ),
                    }
                ],
            ),
            TimerAction(
                period=2.0,
                actions=[
                    Node(
                        package="tag_state_estimation",
                        executable=estimator_executable,
                        name="tag_state_estimation",
                        output="screen",
                        parameters=[
                            {
                                "use_gpu": True,
                                "gpu_backend": gpu_backend,
                                "gpu_device_id": ParameterValue(
                                    gpu_device_id, value_type=int
                                ),
                                "require_gpu": ParameterValue(
                                    require_gpu, value_type=bool
                                ),
                                "pipeline_fps": ParameterValue(
                                    LaunchConfiguration("pipeline_fps"),
                                    value_type=float,
                                ),
                                "process_every_n": ParameterValue(
                                    LaunchConfiguration("process_every_n"),
                                    value_type=int,
                                ),
                                "ai_mode": ai_mode,
                                "ai_model_path": ai_model_path,
                                "ai_backend": LaunchConfiguration(
                                    "ai_backend"
                                ),
                                "ai_confidence_threshold": ParameterValue(
                                    LaunchConfiguration(
                                        "ai_confidence_threshold"
                                    ),
                                    value_type=float,
                                ),
                                "ai_check_every_n_frames": ParameterValue(
                                    LaunchConfiguration(
                                        "ai_check_every_n_frames"
                                    ),
                                    value_type=int,
                                ),
                                "orientation_mode": LaunchConfiguration(
                                    "orientation_mode"
                                ),
                                "imu_topic": LaunchConfiguration("imu_topic"),
                                "imu_timeout_sec": ParameterValue(
                                    LaunchConfiguration("imu_timeout_sec"),
                                    value_type=float,
                                ),
                                "imu_camera_correction_gain": ParameterValue(
                                    LaunchConfiguration(
                                        "imu_camera_correction_gain"
                                    ),
                                    value_type=float,
                                ),
                                "imu_max_disagreement_deg": ParameterValue(
                                    LaunchConfiguration(
                                        "imu_max_disagreement_deg"
                                    ),
                                    value_type=float,
                                ),
                                "imu_mount_roll_deg": ParameterValue(
                                    LaunchConfiguration("imu_mount_roll_deg"),
                                    value_type=float,
                                ),
                                "imu_mount_pitch_deg": ParameterValue(
                                    LaunchConfiguration("imu_mount_pitch_deg"),
                                    value_type=float,
                                ),
                                "imu_mount_yaw_deg": ParameterValue(
                                    LaunchConfiguration("imu_mount_yaw_deg"),
                                    value_type=float,
                                ),
                            }
                        ],
                    )
                ],
            ),
        ]
    )
