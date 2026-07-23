Installation
=====

1. Install [ros2-humble](https://docs.ros.org/en/humble/Installation/Ubuntu-Install-Debians.html) by following the instructions on the linked page. Afterward, complete the [CLI-Configuring-Environment](https://docs.ros.org/en/humble/Tutorials/Beginner-CLI-Tools/Configuring-ROS2-Environment.html) tutorial to source your setup files.

2. Create your ROS2 workspace.

        mkdir cyberrunner_ws && cd cyberrunner_ws && mkdir src && cd src

3. Clone this repository into your ROS2 workspace and navigate back to the workspace root.

        git clone https://github.com/trungbao0301/TAG.git
        cd ..

    The cloned directory is the repository root used by the remaining commands.

4. Install [jax](https://jax.readthedocs.io/en/latest/installation.html) with GPU support.

        pip install --upgrade "jax[cuda12_pip]" -f https://storage.googleapis.com/jax-releases/jax_cuda_releases.html

5. Install dreamerv3. NB: The current version of `dreamerv3` requires `gym==0.19.0`, which is not supported by `pip>=24.1`. `pip` must be downgraded to install `dreamerv3`.

        pip install --upgrade pip==24.0
        pip install -e src/TAG/dreamerv3

    Optional: To revert `pip` to the most updated version run the following.

        pip install --upgrade pip

6. Install dependencies with rosdep.

        sudo rosdep init
        rosdep update
        rosdep install --from-paths src -y --ignore-src

    Install the Python HID binding required by
    `cyberrunner_dynamixel/scripts/hiwonder_compat_node.py` in the same Python
    environment used by ROS. If temperature telemetry is connected through a
    separate serial adapter, also install `pylx16a`.
        
7. Install the CyberRunner packages.

        colcon build --symlink-install

8. Source the workspace and start the active Hiwonder driver.

        source install/setup.bash
        ros2 launch cyberrunner_dynamixel hiwonder.launch.py

    Do not start the Dynamixel or Feetech executables on the TAG hardware.
