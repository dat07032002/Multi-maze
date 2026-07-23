cmake_minimum_required(VERSION 3.5)
project(cyberrunner_dynamixel)

# Default to C99
if(NOT CMAKE_C_STANDARD)
  set(CMAKE_C_STANDARD 99)
endif()

# Default to C++14
if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 14)
endif()

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# Find dependencies
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(cyberrunner_interfaces REQUIRED)
find_package(dynamixel_sdk QUIET)
find_package(ament_cmake_python REQUIRED)
find_package(rclpy REQUIRED)

include_directories(
  include
)

# Preserve the historical Dynamixel executables when their SDK is available,
# but do not make that unused hardware SDK a prerequisite for the Hiwonder
# driver used by TAG.
if(dynamixel_sdk_FOUND)
  add_executable(dynamixel_config src/dynamixel_config.cpp)
  ament_target_dependencies(dynamixel_config rclcpp dynamixel_sdk)

  add_executable(cyberrunner_dynamixel
    src/dynamixel_controller.cpp
    src/cyberrunner_dynamixel.cpp
  )
  ament_target_dependencies(cyberrunner_dynamixel rclcpp cyberrunner_interfaces dynamixel_sdk)

  install(TARGETS
    dynamixel_config
    cyberrunner_dynamixel
    DESTINATION lib/${PROJECT_NAME}
  )
else()
  message(STATUS "dynamixel_sdk not found: building the active Hiwonder driver without legacy Dynamixel executables")
endif()

# Install Python executables
install(PROGRAMS
  scripts/pantilt.py
  scripts/hiwonder_compat_node.py
  scripts/feetech_vel_node.py
  scripts/feetech_config.py
  DESTINATION lib/${PROJECT_NAME}
)

# Install the canonical Hiwonder configuration and launch entry point while
# retaining the historical package name for compatibility with trained runs.
install(DIRECTORY
  config
  launch
  DESTINATION share/${PROJECT_NAME}
)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()
