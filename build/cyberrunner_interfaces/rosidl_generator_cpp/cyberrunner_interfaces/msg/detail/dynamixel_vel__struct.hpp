// generated from rosidl_generator_cpp/resource/idl__struct.hpp.em
// with input from cyberrunner_interfaces:msg/DynamixelVel.idl
// generated code does not contain a copyright notice

#ifndef CYBERRUNNER_INTERFACES__MSG__DETAIL__DYNAMIXEL_VEL__STRUCT_HPP_
#define CYBERRUNNER_INTERFACES__MSG__DETAIL__DYNAMIXEL_VEL__STRUCT_HPP_

#include <algorithm>
#include <array>
#include <cstdint>
#include <memory>
#include <string>
#include <vector>

#include "rosidl_runtime_cpp/bounded_vector.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


#ifndef _WIN32
# define DEPRECATED__cyberrunner_interfaces__msg__DynamixelVel __attribute__((deprecated))
#else
# define DEPRECATED__cyberrunner_interfaces__msg__DynamixelVel __declspec(deprecated)
#endif

namespace cyberrunner_interfaces
{

namespace msg
{

// message struct
template<class ContainerAllocator>
struct DynamixelVel_
{
  using Type = DynamixelVel_<ContainerAllocator>;

  explicit DynamixelVel_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->vel_1 = 0.0;
      this->vel_2 = 0.0;
    }
  }

  explicit DynamixelVel_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  {
    (void)_alloc;
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->vel_1 = 0.0;
      this->vel_2 = 0.0;
    }
  }

  // field types and members
  using _vel_1_type =
    double;
  _vel_1_type vel_1;
  using _vel_2_type =
    double;
  _vel_2_type vel_2;

  // setters for named parameter idiom
  Type & set__vel_1(
    const double & _arg)
  {
    this->vel_1 = _arg;
    return *this;
  }
  Type & set__vel_2(
    const double & _arg)
  {
    this->vel_2 = _arg;
    return *this;
  }

  // constant declarations

  // pointer types
  using RawPtr =
    cyberrunner_interfaces::msg::DynamixelVel_<ContainerAllocator> *;
  using ConstRawPtr =
    const cyberrunner_interfaces::msg::DynamixelVel_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<cyberrunner_interfaces::msg::DynamixelVel_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<cyberrunner_interfaces::msg::DynamixelVel_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      cyberrunner_interfaces::msg::DynamixelVel_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<cyberrunner_interfaces::msg::DynamixelVel_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      cyberrunner_interfaces::msg::DynamixelVel_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<cyberrunner_interfaces::msg::DynamixelVel_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<cyberrunner_interfaces::msg::DynamixelVel_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<cyberrunner_interfaces::msg::DynamixelVel_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__cyberrunner_interfaces__msg__DynamixelVel
    std::shared_ptr<cyberrunner_interfaces::msg::DynamixelVel_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__cyberrunner_interfaces__msg__DynamixelVel
    std::shared_ptr<cyberrunner_interfaces::msg::DynamixelVel_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const DynamixelVel_ & other) const
  {
    if (this->vel_1 != other.vel_1) {
      return false;
    }
    if (this->vel_2 != other.vel_2) {
      return false;
    }
    return true;
  }
  bool operator!=(const DynamixelVel_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct DynamixelVel_

// alias to use template instance with default allocator
using DynamixelVel =
  cyberrunner_interfaces::msg::DynamixelVel_<std::allocator<void>>;

// constant definitions

}  // namespace msg

}  // namespace cyberrunner_interfaces

#endif  // CYBERRUNNER_INTERFACES__MSG__DETAIL__DYNAMIXEL_VEL__STRUCT_HPP_
