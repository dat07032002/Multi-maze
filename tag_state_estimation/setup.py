from setuptools import setup, find_packages
from glob import glob

package_name = "tag_state_estimation"

setup(
    name=package_name,
    version="0.0.0",
    packages=find_packages(exclude=["test/"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name, glob("calib/*.txt")),
        ("share/" + package_name, ["markers.csv"]),
        ("share/" + package_name + "/models", glob("models/*.onnx")),
        #("share/" + package_name, "rviz/config.rviz"),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="timflueckiger",
    maintainer_email="timflueckiger@outlook.com",
    description="Camera-based marble and board-pose estimation for TAG",
    license="AGPL-3.0-only",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "estimator = tag_state_estimation.tag_state_estimation_node:main",
            "estimator_sub = tag_state_estimation.tag_state_estimation_subimg:main",
            "select_markers = tag_state_estimation.select_markers:main",
            "ai_labeler = tag_state_estimation.ai_dataset_labeler:main",
            "ai_offline_labeler = tag_state_estimation.ai_offline_labeler:main",
            "ai_failure_capture = tag_state_estimation.ai_failure_capture:main",
            "ai_train = tag_state_estimation.train_ai_marble:main",
            "ai_detector = tag_state_estimation.ai_marble_detector_node:main",
            "bno086_serial = tag_state_estimation.bno086_serial_node:main",
        ],
    },
)
