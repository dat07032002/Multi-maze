// generated from rosidl_generator_cpp/resource/idl__builder.hpp.em
// with input from cyberrunner_interfaces:msg/DynamixelVel.idl
// generated code does not contain a copyright notice

#ifndef CYBERRUNNER_INTERFACES__MSG__DETAIL__DYNAMIXEL_VEL__BUILDER_HPP_
#define CYBERRUNNER_INTERFACES__MSG__DETAIL__DYNAMIXEL_VEL__BUILDER_HPP_

#include <algorithm>
#include <utility>

#include "cyberrunner_interfaces/msg/detail/dynamixel_vel__struct.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


namespace cyberrunner_interfaces
{

namespace msg
{

namespace builder
{

class Init_DynamixelVel_vel_2
{
public:
  explicit Init_DynamixelVel_vel_2(::cyberrunner_interfaces::msg::DynamixelVel & msg)
  : msg_(msg)
  {}
  ::cyberrunner_interfaces::msg::DynamixelVel vel_2(::cyberrunner_interfaces::msg::DynamixelVel::_vel_2_type arg)
  {
    msg_.vel_2 = std::move(arg);
    return std::move(msg_);
  }

private:
  ::cyberrunner_interfaces::msg::DynamixelVel msg_;
};

class Init_DynamixelVel_vel_1
{
public:
  Init_DynamixelVel_vel_1()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  Init_DynamixelVel_vel_2 vel_1(::cyberrunner_interfaces::msg::DynamixelVel::_vel_1_type arg)
  {
    msg_.vel_1 = std::move(arg);
    return Init_DynamixelVel_vel_2(msg_);
  }

private:
  ::cyberrunner_interfaces::msg::DynamixelVel msg_;
};

}  // namespace builder

}  // namespace msg

template<typename MessageType>
auto build();

template<>
inline
auto build<::cyberrunner_interfaces::msg::DynamixelVel>()
{
  return cyberrunner_interfaces::msg::builder::Init_DynamixelVel_vel_1();
}

}  // namespace cyberrunner_interfaces

#endif  // CYBERRUNNER_INTERFACES__MSG__DETAIL__DYNAMIXEL_VEL__BUILDER_HPP_
