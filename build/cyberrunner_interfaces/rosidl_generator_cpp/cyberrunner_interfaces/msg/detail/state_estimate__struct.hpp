// generated from rosidl_generator_cpp/resource/idl__struct.hpp.em
// with input from cyberrunner_interfaces:msg/StateEstimate.idl
// generated code does not contain a copyright notice

#ifndef CYBERRUNNER_INTERFACES__MSG__DETAIL__STATE_ESTIMATE__STRUCT_HPP_
#define CYBERRUNNER_INTERFACES__MSG__DETAIL__STATE_ESTIMATE__STRUCT_HPP_

#include <algorithm>
#include <array>
#include <cstdint>
#include <memory>
#include <string>
#include <vector>

#include "rosidl_runtime_cpp/bounded_vector.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


#ifndef _WIN32
# define DEPRECATED__cyberrunner_interfaces__msg__StateEstimate __attribute__((deprecated))
#else
# define DEPRECATED__cyberrunner_interfaces__msg__StateEstimate __declspec(deprecated)
#endif

namespace cyberrunner_interfaces
{

namespace msg
{

// message struct
template<class ContainerAllocator>
struct StateEstimate_
{
  using Type = StateEstimate_<ContainerAllocator>;

  explicit StateEstimate_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->x_b = 0.0;
      this->y_b = 0.0;
      this->x_b_dot = 0.0;
      this->y_b_dot = 0.0;
      this->alpha = 0.0;
      this->beta = 0.0;
    }
  }

  explicit StateEstimate_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  {
    (void)_alloc;
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->x_b = 0.0;
      this->y_b = 0.0;
      this->x_b_dot = 0.0;
      this->y_b_dot = 0.0;
      this->alpha = 0.0;
      this->beta = 0.0;
    }
  }

  // field types and members
  using _x_b_type =
    double;
  _x_b_type x_b;
  using _y_b_type =
    double;
  _y_b_type y_b;
  using _x_b_dot_type =
    double;
  _x_b_dot_type x_b_dot;
  using _y_b_dot_type =
    double;
  _y_b_dot_type y_b_dot;
  using _alpha_type =
    double;
  _alpha_type alpha;
  using _beta_type =
    double;
  _beta_type beta;

  // setters for named parameter idiom
  Type & set__x_b(
    const double & _arg)
  {
    this->x_b = _arg;
    return *this;
  }
  Type & set__y_b(
    const double & _arg)
  {
    this->y_b = _arg;
    return *this;
  }
  Type & set__x_b_dot(
    const double & _arg)
  {
    this->x_b_dot = _arg;
    return *this;
  }
  Type & set__y_b_dot(
    const double & _arg)
  {
    this->y_b_dot = _arg;
    return *this;
  }
  Type & set__alpha(
    const double & _arg)
  {
    this->alpha = _arg;
    return *this;
  }
  Type & set__beta(
    const double & _arg)
  {
    this->beta = _arg;
    return *this;
  }

  // constant declarations

  // pointer types
  using RawPtr =
    cyberrunner_interfaces::msg::StateEstimate_<ContainerAllocator> *;
  using ConstRawPtr =
    const cyberrunner_interfaces::msg::StateEstimate_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<cyberrunner_interfaces::msg::StateEstimate_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<cyberrunner_interfaces::msg::StateEstimate_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      cyberrunner_interfaces::msg::StateEstimate_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<cyberrunner_interfaces::msg::StateEstimate_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      cyberrunner_interfaces::msg::StateEstimate_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<cyberrunner_interfaces::msg::StateEstimate_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<cyberrunner_interfaces::msg::StateEstimate_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<cyberrunner_interfaces::msg::StateEstimate_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__cyberrunner_interfaces__msg__StateEstimate
    std::shared_ptr<cyberrunner_interfaces::msg::StateEstimate_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__cyberrunner_interfaces__msg__StateEstimate
    std::shared_ptr<cyberrunner_interfaces::msg::StateEstimate_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const StateEstimate_ & other) const
  {
    if (this->x_b != other.x_b) {
      return false;
    }
    if (this->y_b != other.y_b) {
      return false;
    }
    if (this->x_b_dot != other.x_b_dot) {
      return false;
    }
    if (this->y_b_dot != other.y_b_dot) {
      return false;
    }
    if (this->alpha != other.alpha) {
      return false;
    }
    if (this->beta != other.beta) {
      return false;
    }
    return true;
  }
  bool operator!=(const StateEstimate_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct StateEstimate_

// alias to use template instance with default allocator
using StateEstimate =
  cyberrunner_interfaces::msg::StateEstimate_<std::allocator<void>>;

// constant definitions

}  // namespace msg

}  // namespace cyberrunner_interfaces

#endif  // CYBERRUNNER_INTERFACES__MSG__DETAIL__STATE_ESTIMATE__STRUCT_HPP_
