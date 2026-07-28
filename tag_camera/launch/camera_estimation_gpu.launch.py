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
    pose_zero_alpha_deg = LaunchConfiguration("pose_zero_alpha_deg")
    pose_zero_beta_deg = LaunchConfiguration("pose_zero_beta_deg")

    return LaunchDescription(
        [
            DeclareLaunchArgument("device", default_value="/dev/video2"),
            DeclareLaunchArgument("gpu_backend", default_value="auto"),
            DeclareLaunchArgument("gpu_device_id", default_value="0"),
            DeclareLaunchArgument("require_gpu", default_value="false"),
            DeclareLaunchArgument("camera_fps", default_value="60.0"),
            DeclareLaunchArgument("camera_width", default_value="1920"),
            DeclareLaunchArgument("camera_height", default_value="1200"),
            DeclareLaunchArgument("output_width", default_value="640"),
            DeclareLaunchArgument("output_height", default_value="400"),
            DeclareLaunchArgument("border_y", default_value="0"),
            DeclareLaunchArgument("capture_backend", default_value="gstreamer"),
            DeclareLaunchArgument("pipeline_fps", default_value="60.0"),
            DeclareLaunchArgument("velocity_window_sec", default_value="0.25"),
            DeclareLaunchArgument("velocity_min_samples", default_value="6"),
            DeclareLaunchArgument(
                "velocity_deadband_mps", default_value="0.002"
            ),
            DeclareLaunchArgument("process_every_n", default_value="1"),
            DeclareLaunchArgument("pose_zero_alpha_deg", default_value="-0.10"),
            DeclareLaunchArgument("pose_zero_beta_deg", default_value="2.30"),
            DeclareLaunchArgument(
                "pose_max_reprojection_rmse_px", default_value="5.0"
            ),
            DeclareLaunchArgument("pose_reacquire_frames", default_value="5"),
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
            DeclareLaunchArgument("ai_fusion_weight", default_value="0.5"),
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
                        "capture_backend": LaunchConfiguration(
                            "capture_backend"
                        ),
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
                                "velocity_window_sec": ParameterValue(
                                    LaunchConfiguration("velocity_window_sec"),
                                    value_type=float,
                                ),
                                "velocity_min_samples": ParameterValue(
                                    LaunchConfiguration("velocity_min_samples"),
                                    value_type=int,
                                ),
                                "velocity_deadband_mps": ParameterValue(
                                    LaunchConfiguration(
                                        "velocity_deadband_mps"
                                    ),
                                    value_type=float,
                                ),
                                # YAML 1.1 treats the unquoted value "off" as
                                # a boolean. Force the launch argument to stay
                                # a string for the estimator's off/shadow/hybrid
                                # mode selector.
                                "ai_mode": ParameterValue(
                                    ai_mode, value_type=str
                                ),
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
                                "ai_fusion_weight": ParameterValue(
                                    LaunchConfiguration("ai_fusion_weight"),
                                    value_type=float,
                                ),
                                "orientation_mode": LaunchConfiguration(
                                    "orientation_mode"
                                ),
                                "pose_zero_alpha_deg": ParameterValue(
                                    pose_zero_alpha_deg, value_type=float
                                ),
                                "pose_zero_beta_deg": ParameterValue(
                                    pose_zero_beta_deg, value_type=float
                                ),
                                "pose_max_reprojection_rmse_px": ParameterValue(
                                    LaunchConfiguration(
                                        "pose_max_reprojection_rmse_px"
                                    ),
                                    value_type=float,
                                ),
                                "pose_reacquire_frames": ParameterValue(
                                    LaunchConfiguration(
                                        "pose_reacquire_frames"
                                    ),
                                    value_type=int,
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
