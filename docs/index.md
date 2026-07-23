# TAG CyberRunner Documentation

TAG is a trained physical CyberRunner system using Hiwonder servos and a custom
maze. Historical Dynamixel material is retained only to preserve upstream and
mechanical reference information.

## Requirements

* Ubuntu 22.04
* MATLAB
* GPU: min. 1x RTX 2080 Super

## Tutorials

* [Project Structure](00_project_structure.md): Understand maintained, compatibility, and generated paths.
* [Hiwonder Setup](08_hiwonder_setup.md): Configure and safely test the active servos.
* [Custom Printed Maze](09_custom_maze_workflow.md): Keep CAD, print files, geometry, and training paths synchronized.
* [Protected Artifacts](10_protected_artifacts.md): Files that must survive cleanup.
* [Hardware Setup](01_hardware_setup.md): Historical upstream mechanical reference.
* [Reload Mechanism](02_reload.md): Add an automatic reload mechanism to your CyberRunner robot.
* [Installation](03_installation.md): Install all necessary dependencies and the CyberRunner software stack.
* [Initial Configuration](04_initial_config.md): Calibrate the camera and markers.
* [Train](05_train.md): Let CyberRunner learn to play the labyrinth game.
* [Troubleshooting](06_troubleshooting.md): Fix common issues.

!!! note "Note"

    This project is under active development.

<!-- !!! Potential addition

    Video tutorials? This applies to software and configuration as well -->
