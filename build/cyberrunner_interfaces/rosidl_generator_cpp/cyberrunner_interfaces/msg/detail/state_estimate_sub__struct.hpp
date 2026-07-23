// generated from rosidl_generator_cpp/resource/idl__struct.hpp.em
// with input from cyberrunner_interfaces:msg/StateEstimateSub.idl
// generated code does not contain a copyright notice

#ifndef CYBERRUNNER_INTERFACES__MSG__DETAIL__STATE_ESTIMATE_SUB__STRUCT_HPP_
#define CYBERRUNNER_INTERFACES__MSG__DETAIL__STATE_ESTIMATE_SUB__STRUCT_HPP_

#include <algorithm>
#include <array>
#include <cstdint>
#include <memory>
#include <string>
#include <vector>

#include "rosidl_runtime_cpp/bounded_vector.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


// Include directives for member types
// Member 'state'
#include "cyberrunner_interfaces/msg/detail/state_estimate__struct.hpp"
// Member 'subimg'
#include "sensor_msgs/msg/detail/image__struct.hpp"

#ifndef _WIN32
# define DEPRECATED__cyberrunner_interfaces__msg__StateEstimateSub __attribute__((deprecated))
#else
# define DEPRECATED__cyberrunner_interfaces__msg__StateEstimateSub __declspec(deprecated)
#endif

namespace cyberrunner_interfaces
{

namespace msg
{

// message struct
template<class ContainerAllocator>
struct StateEstimateSub_
{
  using Type = StateEstimateSub_<ContainerAllocator>;

  explicit StateEstimateSub_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : state(_init),
    subimg(_init)
  {
    (void)_init;
  }

  explicit StateEstimateSub_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : state(_alloc, _init),
    subimg(_alloc, _init)
  {
    (void)_init;
  }

  // field types and members
  using _state_type =
    cyberrunner_interfaces::msg::StateEstimate_<ContainerAllocator>;
  _state_type state;
  using _subimg_type =
    sensor_msgs::msg::Image_<ContainerAllocator>;
  _subimg_type subimg;

  // setters for named parameter idiom
  Type & set__state(
    const cyberrunner_interfaces::msg::StateEstimate_<ContainerAllocator> & _arg)
  {
    this->state = _arg;
    return *this;
  }
  Type & set__subimg(
    const sensor_msgs::msg::Image_<ContainerAllocator> & _arg)
  {
    this->subimg = _arg;
    return *this;
  }

  // constant declarations

  // pointer types
  using RawPtr =
    cyberrunner_interfaces::msg::StateEstimateSub_<ContainerAllocator> *;
  using ConstRawPtr =
    const cyberrunner_interfaces::msg::StateEstimateSub_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<cyberrunner_interfaces::msg::StateEstimateSub_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<cyberrunner_interfaces::msg::StateEstimateSub_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      cyberrunner_interfaces::msg::StateEstimateSub_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<cyberrunner_interfaces::msg::StateEstimateSub_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      cyberrunner_interfaces::msg::StateEstimateSub_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<cyberrunner_interfaces::msg::StateEstimateSub_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<cyberrunner_interfaces::msg::StateEstimateSub_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<cyberrunner_interfaces::msg::StateEstimateSub_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__cyberrunner_interfaces__msg__StateEstimateSub
    std::shared_ptr<cyberrunner_interfaces::msg::StateEstimateSub_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__cyberrunner_interfaces__msg__StateEstimateSub
    std::shared_ptr<cyberrunner_interfaces::msg::StateEstimateSub_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const StateEstimateSub_ & other) const
  {
    if (this->state != other.state) {
      return false;
    }
    if (this->subimg != other.subimg) {
      return false;
    }
    return true;
  }
  bool operator!=(const StateEstimateSub_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct StateEstimateSub_

// alias to use template instance with default allocator
using StateEstimateSub =
  cyberrunner_interfaces::msg::StateEstimateSub_<std::allocator<void>>;

// constant definitions

}  // namespace msg

}  // namespace cyberrunner_interfaces

#endif  // CYBERRUNNER_INTERFACES__MSG__DETAIL__STATE_ESTIMATE_SUB__STRUCT_HPP_
