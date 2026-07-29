from setuptools import find_packages, setup


package_name = "tag_adaptation"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml", "README.md"]),
        ("share/" + package_name + "/config", ["config/shadow.yaml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="TAG project",
    maintainer_email="noreply@example.com",
    description="Offline and safety-locked TAG hardware policy adaptation tools",
    url="https://github.com/dat07032002/Multi-maze",
    license="MIT",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "analyze-weaknesses = tag_adaptation.cli:weaknesses_main",
            "evaluate-promotion = tag_adaptation.cli:promotion_main",
        ],
    },
)
