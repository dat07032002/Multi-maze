// generated from rosidl_generator_cpp/resource/idl__builder.hpp.em
// with input from cyberrunner_interfaces:srv/DynamixelReset.idl
// generated code does not contain a copyright notice

#ifndef CYBERRUNNER_INTERFACES__SRV__DETAIL__DYNAMIXEL_RESET__BUILDER_HPP_
#define CYBERRUNNER_INTERFACES__SRV__DETAIL__DYNAMIXEL_RESET__BUILDER_HPP_

#include <algorithm>
#include <utility>

#include "cyberrunner_interfaces/srv/detail/dynamixel_reset__struct.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


namespace cyberrunner_interfaces
{

namespace srv
{

namespace builder
{

class Init_DynamixelReset_Request_max_temp
{
public:
  Init_DynamixelReset_Request_max_temp()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  ::cyberrunner_interfaces::srv::DynamixelReset_Request max_temp(::cyberrunner_interfaces::srv::DynamixelReset_Request::_max_temp_type arg)
  {
    msg_.max_temp = std::move(arg);
    return std::move(msg_);
  }

private:
  ::cyberrunner_interfaces::srv::DynamixelReset_Request msg_;
};

}  // namespace builder

}  // namespace srv

template<typename MessageType>
auto build();

template<>
inline
auto build<::cyberrunner_interfaces::srv::DynamixelReset_Request>()
{
  return cyberrunner_interfaces::srv::builder::Init_DynamixelReset_Request_max_temp();
}

}  // namespace cyberrunner_interfaces


namespace cyberrunner_interfaces
{

namespace srv
{

namespace builder
{

class Init_DynamixelReset_Response_success
{
public:
  Init_DynamixelReset_Response_success()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  ::cyberrunner_interfaces::srv::DynamixelReset_Response success(::cyberrunner_interfaces::srv::DynamixelReset_Response::_success_type arg)
  {
    msg_.success = std::move(arg);
    return std::move(msg_);
  }

private:
  ::cyberrunner_interfaces::srv::DynamixelReset_Response msg_;
};

}  // namespace builder

}  // namespace srv

template<typename MessageType>
auto build();

template<>
inline
auto build<::cyberrunner_interfaces::srv::DynamixelReset_Response>()
{
  return cyberrunner_interfaces::srv::builder::Init_DynamixelReset_Response_success();
}

}  // namespace cyberrunner_interfaces

#endif  // CYBERRUNNER_INTERFACES__SRV__DETAIL__DYNAMIXEL_RESET__BUILDER_HPP_
