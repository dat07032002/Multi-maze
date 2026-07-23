// generated from rosidl_generator_cpp/resource/idl__builder.hpp.em
// with input from cyberrunner_interfaces:msg/StateEstimate.idl
// generated code does not contain a copyright notice

#ifndef CYBERRUNNER_INTERFACES__MSG__DETAIL__STATE_ESTIMATE__BUILDER_HPP_
#define CYBERRUNNER_INTERFACES__MSG__DETAIL__STATE_ESTIMATE__BUILDER_HPP_

#include <algorithm>
#include <utility>

#include "cyberrunner_interfaces/msg/detail/state_estimate__struct.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


namespace cyberrunner_interfaces
{

namespace msg
{

namespace builder
{

class Init_StateEstimate_beta
{
public:
  explicit Init_StateEstimate_beta(::cyberrunner_interfaces::msg::StateEstimate & msg)
  : msg_(msg)
  {}
  ::cyberrunner_interfaces::msg::StateEstimate beta(::cyberrunner_interfaces::msg::StateEstimate::_beta_type arg)
  {
    msg_.beta = std::move(arg);
    return std::move(msg_);
  }

private:
  ::cyberrunner_interfaces::msg::StateEstimate msg_;
};

class Init_StateEstimate_alpha
{
public:
  explicit Init_StateEstimate_alpha(::cyberrunner_interfaces::msg::StateEstimate & msg)
  : msg_(msg)
  {}
  Init_StateEstimate_beta alpha(::cyberrunner_interfaces::msg::StateEstimate::_alpha_type arg)
  {
    msg_.alpha = std::move(arg);
    return Init_StateEstimate_beta(msg_);
  }

private:
  ::cyberrunner_interfaces::msg::StateEstimate msg_;
};

class Init_StateEstimate_y_b_dot
{
public:
  explicit Init_StateEstimate_y_b_dot(::cyberrunner_interfaces::msg::StateEstimate & msg)
  : msg_(msg)
  {}
  Init_StateEstimate_alpha y_b_dot(::cyberrunner_interfaces::msg::StateEstimate::_y_b_dot_type arg)
  {
    msg_.y_b_dot = std::move(arg);
    return Init_StateEstimate_alpha(msg_);
  }

private:
  ::cyberrunner_interfaces::msg::StateEstimate msg_;
};

class Init_StateEstimate_x_b_dot
{
public:
  explicit Init_StateEstimate_x_b_dot(::cyberrunner_interfaces::msg::StateEstimate & msg)
  : msg_(msg)
  {}
  Init_StateEstimate_y_b_dot x_b_dot(::cyberrunner_interfaces::msg::StateEstimate::_x_b_dot_type arg)
  {
    msg_.x_b_dot = std::move(arg);
    return Init_StateEstimate_y_b_dot(msg_);
  }

private:
  ::cyberrunner_interfaces::msg::StateEstimate msg_;
};

class Init_StateEstimate_y_b
{
public:
  explicit Init_StateEstimate_y_b(::cyberrunner_interfaces::msg::StateEstimate & msg)
  : msg_(msg)
  {}
  Init_StateEstimate_x_b_dot y_b(::cyberrunner_interfaces::msg::StateEstimate::_y_b_type arg)
  {
    msg_.y_b = std::move(arg);
    return Init_StateEstimate_x_b_dot(msg_);
  }

private:
  ::cyberrunner_interfaces::msg::StateEstimate msg_;
};

class Init_StateEstimate_x_b
{
public:
  Init_StateEstimate_x_b()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  Init_StateEstimate_y_b x_b(::cyberrunner_interfaces::msg::StateEstimate::_x_b_type arg)
  {
    msg_.x_b = std::move(arg);
    return Init_StateEstimate_y_b(msg_);
  }

private:
  ::cyberrunner_interfaces::msg::StateEstimate msg_;
};

}  // namespace builder

}  // namespace msg

template<typename MessageType>
auto build();

template<>
inline
auto build<::cyberrunner_interfaces::msg::StateEstimate>()
{
  return cyberrunner_interfaces::msg::builder::Init_StateEstimate_x_b();
}

}  // namespace cyberrunner_interfaces

#endif  // CYBERRUNNER_INTERFACES__MSG__DETAIL__STATE_ESTIMATE__BUILDER_HPP_
