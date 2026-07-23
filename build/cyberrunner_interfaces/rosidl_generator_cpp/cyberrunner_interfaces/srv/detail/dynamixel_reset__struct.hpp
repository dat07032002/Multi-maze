// generated from rosidl_generator_cpp/resource/idl__struct.hpp.em
// with input from cyberrunner_interfaces:srv/DynamixelReset.idl
// generated code does not contain a copyright notice

#ifndef CYBERRUNNER_INTERFACES__SRV__DETAIL__DYNAMIXEL_RESET__STRUCT_HPP_
#define CYBERRUNNER_INTERFACES__SRV__DETAIL__DYNAMIXEL_RESET__STRUCT_HPP_

#include <algorithm>
#include <array>
#include <cstdint>
#include <memory>
#include <string>
#include <vector>

#include "rosidl_runtime_cpp/bounded_vector.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


#ifndef _WIN32
# define DEPRECATED__cyberrunner_interfaces__srv__DynamixelReset_Request __attribute__((deprecated))
#else
# define DEPRECATED__cyberrunner_interfaces__srv__DynamixelReset_Request __declspec(deprecated)
#endif

namespace cyberrunner_interfaces
{

namespace srv
{

// message struct
template<class ContainerAllocator>
struct DynamixelReset_Request_
{
  using Type = DynamixelReset_Request_<ContainerAllocator>;

  explicit DynamixelReset_Request_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->max_temp = 0;
    }
  }

  explicit DynamixelReset_Request_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  {
    (void)_alloc;
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->max_temp = 0;
    }
  }

  // field types and members
  using _max_temp_type =
    uint16_t;
  _max_temp_type max_temp;

  // setters for named parameter idiom
  Type & set__max_temp(
    const uint16_t & _arg)
  {
    this->max_temp = _arg;
    return *this;
  }

  // constant declarations

  // pointer types
  using RawPtr =
    cyberrunner_interfaces::srv::DynamixelReset_Request_<ContainerAllocator> *;
  using ConstRawPtr =
    const cyberrunner_interfaces::srv::DynamixelReset_Request_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<cyberrunner_interfaces::srv::DynamixelReset_Request_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<cyberrunner_interfaces::srv::DynamixelReset_Request_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      cyberrunner_interfaces::srv::DynamixelReset_Request_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<cyberrunner_interfaces::srv::DynamixelReset_Request_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      cyberrunner_interfaces::srv::DynamixelReset_Request_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<cyberrunner_interfaces::srv::DynamixelReset_Request_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<cyberrunner_interfaces::srv::DynamixelReset_Request_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<cyberrunner_interfaces::srv::DynamixelReset_Request_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__cyberrunner_interfaces__srv__DynamixelReset_Request
    std::shared_ptr<cyberrunner_interfaces::srv::DynamixelReset_Request_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__cyberrunner_interfaces__srv__DynamixelReset_Request
    std::shared_ptr<cyberrunner_interfaces::srv::DynamixelReset_Request_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const DynamixelReset_Request_ & other) const
  {
    if (this->max_temp != other.max_temp) {
      return false;
    }
    return true;
  }
  bool operator!=(const DynamixelReset_Request_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct DynamixelReset_Request_

// alias to use template instance with default allocator
using DynamixelReset_Request =
  cyberrunner_interfaces::srv::DynamixelReset_Request_<std::allocator<void>>;

// constant definitions

}  // namespace srv

}  // namespace cyberrunner_interfaces


#ifndef _WIN32
# define DEPRECATED__cyberrunner_interfaces__srv__DynamixelReset_Response __attribute__((deprecated))
#else
# define DEPRECATED__cyberrunner_interfaces__srv__DynamixelReset_Response __declspec(deprecated)
#endif

namespace cyberrunner_interfaces
{

namespace srv
{

// message struct
template<class ContainerAllocator>
struct DynamixelReset_Response_
{
  using Type = DynamixelReset_Response_<ContainerAllocator>;

  explicit DynamixelReset_Response_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->success = 0;
    }
  }

  explicit DynamixelReset_Response_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  {
    (void)_alloc;
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->success = 0;
    }
  }

  // field types and members
  using _success_type =
    int8_t;
  _success_type success;

  // setters for named parameter idiom
  Type & set__success(
    const int8_t & _arg)
  {
    this->success = _arg;
    return *this;
  }

  // constant declarations

  // pointer types
  using RawPtr =
    cyberrunner_interfaces::srv::DynamixelReset_Response_<ContainerAllocator> *;
  using ConstRawPtr =
    const cyberrunner_interfaces::srv::DynamixelReset_Response_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<cyberrunner_interfaces::srv::DynamixelReset_Response_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<cyberrunner_interfaces::srv::DynamixelReset_Response_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      cyberrunner_interfaces::srv::DynamixelReset_Response_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<cyberrunner_interfaces::srv::DynamixelReset_Response_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      cyberrunner_interfaces::srv::DynamixelReset_Response_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<cyberrunner_interfaces::srv::DynamixelReset_Response_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<cyberrunner_interfaces::srv::DynamixelReset_Response_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<cyberrunner_interfaces::srv::DynamixelReset_Response_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__cyberrunner_interfaces__srv__DynamixelReset_Response
    std::shared_ptr<cyberrunner_interfaces::srv::DynamixelReset_Response_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__cyberrunner_interfaces__srv__DynamixelReset_Response
    std::shared_ptr<cyberrunner_interfaces::srv::DynamixelReset_Response_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const DynamixelReset_Response_ & other) const
  {
    if (this->success != other.success) {
      return false;
    }
    return true;
  }
  bool operator!=(const DynamixelReset_Response_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct DynamixelReset_Response_

// alias to use template instance with default allocator
using DynamixelReset_Response =
  cyberrunner_interfaces::srv::DynamixelReset_Response_<std::allocator<void>>;

// constant definitions

}  // namespace srv

}  // namespace cyberrunner_interfaces

namespace cyberrunner_interfaces
{

namespace srv
{

struct DynamixelReset
{
  using Request = cyberrunner_interfaces::srv::DynamixelReset_Request;
  using Response = cyberrunner_interfaces::srv::DynamixelReset_Response;
};

}  // namespace srv

}  // namespace cyberrunner_interfaces

#endif  // CYBERRUNNER_INTERFACES__SRV__DETAIL__DYNAMIXEL_RESET__STRUCT_HPP_
