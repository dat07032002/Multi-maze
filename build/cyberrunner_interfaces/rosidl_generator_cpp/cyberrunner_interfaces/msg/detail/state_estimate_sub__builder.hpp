// generated from rosidl_generator_cpp/resource/idl__builder.hpp.em
// with input from cyberrunner_interfaces:msg/StateEstimateSub.idl
// generated code does not contain a copyright notice

#ifndef CYBERRUNNER_INTERFACES__MSG__DETAIL__STATE_ESTIMATE_SUB__BUILDER_HPP_
#define CYBERRUNNER_INTERFACES__MSG__DETAIL__STATE_ESTIMATE_SUB__BUILDER_HPP_

#include <algorithm>
#include <utility>

#include "cyberrunner_interfaces/msg/detail/state_estimate_sub__struct.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


namespace cyberrunner_interfaces
{

namespace msg
{

namespace builder
{

class Init_StateEstimateSub_subimg
{
public:
  explicit Init_StateEstimateSub_subimg(::cyberrunner_interfaces::msg::StateEstimateSub & msg)
  : msg_(msg)
  {}
  ::cyberrunner_interfaces::msg::StateEstimateSub subimg(::cyberrunner_interfaces::msg::StateEstimateSub::_subimg_type arg)
  {
    msg_.subimg = std::move(arg);
    return std::move(msg_);
  }

private:
  ::cyberrunner_interfaces::msg::StateEstimateSub msg_;
};

class Init_StateEstimateSub_state
{
public:
  Init_StateEstimateSub_state()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  Init_StateEstimateSub_subimg state(::cyberrunner_interfaces::msg::StateEstimateSub::_state_type arg)
  {
    msg_.state = std::move(arg);
    return Init_StateEstimateSub_subimg(msg_);
  }

private:
  ::cyberrunner_interfaces::msg::StateEstimateSub msg_;
};

}  // namespace builder

}  // namespace msg

template<typename MessageType>
auto build();

template<>
inline
auto build<::cyberrunner_interfaces::msg::StateEstimateSub>()
{
  return cyberrunner_interfaces::msg::builder::Init_StateEstimateSub_state();
}

}  // namespace cyberrunner_interfaces

#endif  // CYBERRUNNER_INTERFACES__MSG__DETAIL__STATE_ESTIMATE_SUB__BUILDER_HPP_
