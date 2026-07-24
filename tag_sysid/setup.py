from setuptools import find_packages, setup


package_name = "tag_sysid"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml", "README.md"]),
    ],
    install_requires=["setuptools", "numpy"],
    zip_safe=True,
    maintainer="TAG project",
    maintainer_email="noreply@example.com",
    description="Passive ROS 2 recorder and offline analyzer for TAG system identification",
    license="MIT",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "record = tag_sysid.recorder:main",
            "analyze = tag_sysid.analyze:main",
            "active = tag_sysid.active:main",
        ],
    },
)
