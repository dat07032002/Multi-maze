// generated from rosidl_generator_cpp/resource/idl__traits.hpp.em
// with input from cyberrunner_interfaces:msg/StateEstimateSub.idl
// generated code does not contain a copyright notice

#ifndef CYBERRUNNER_INTERFACES__MSG__DETAIL__STATE_ESTIMATE_SUB__TRAITS_HPP_
#define CYBERRUNNER_INTERFACES__MSG__DETAIL__STATE_ESTIMATE_SUB__TRAITS_HPP_

#include <stdint.h>

#include <sstream>
#include <string>
#include <type_traits>

#include "cyberrunner_interfaces/msg/detail/state_estimate_sub__struct.hpp"
#include "rosidl_runtime_cpp/traits.hpp"

// Include directives for member types
// Member 'state'
#include "cyberrunner_interfaces/msg/detail/state_estimate__traits.hpp"
// Member 'subimg'
#include "sensor_msgs/msg/detail/image__traits.hpp"

namespace cyberrunner_interfaces
{

namespace msg
{

inline void to_flow_style_yaml(
  const StateEstimateSub & msg,
  std::ostream & out)
{
  out << "{";
  // member: state
  {
    out << "state: ";
    to_flow_style_yaml(msg.state, out);
    out << ", ";
  }

  // member: subimg
  {
    out << "subimg: ";
    to_flow_style_yaml(msg.subimg, out);
  }
  out << "}";
}  // NOLINT(readability/fn_size)

inline void to_block_style_yaml(
  const StateEstimateSub & msg,
  std::ostream & out, size_t indentation = 0)
{
  // member: state
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "state:\n";
    to_block_style_yaml(msg.state, out, indentation + 2);
  }

  // member: subimg
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "subimg:\n";
    to_block_style_yaml(msg.subimg, out, indentation + 2);
  }
}  // NOLINT(readability/fn_size)

inline std::string to_yaml(const StateEstimateSub & msg, bool use_flow_style = false)
{
  std::ostringstream out;
  if (use_flow_style) {
    to_flow_style_yaml(msg, out);
  } else {
    to_block_style_yaml(msg, out);
  }
  return out.str();
}

}  // namespace msg

}  // namespace cyberrunner_interfaces

namespace rosidl_generator_traits
{

[[deprecated("use cyberrunner_interfaces::msg::to_block_style_yaml() instead")]]
inline void to_yaml(
  const cyberrunner_interfaces::msg::StateEstimateSub & msg,
  std::ostream & out, size_t indentation = 0)
{
  cyberrunner_interfaces::msg::to_block_style_yaml(msg, out, indentation);
}

[[deprecated("use cyberrunner_interfaces::msg::to_yaml() instead")]]
inline std::string to_yaml(const cyberrunner_interfaces::msg::StateEstimateSub & msg)
{
  return cyberrunner_interfaces::msg::to_yaml(msg);
}

template<>
inline const char * data_type<cyberrunner_interfaces::msg::StateEstimateSub>()
{
  return "cyberrunner_interfaces::msg::StateEstimateSub";
}

template<>
inline const char * name<cyberrunner_interfaces::msg::StateEstimateSub>()
{
  return "cyberrunner_interfaces/msg/StateEstimateSub";
}

template<>
struct has_fixed_size<cyberrunner_interfaces::msg::StateEstimateSub>
  : std::integral_constant<bool, has_fixed_size<cyberrunner_interfaces::msg::StateEstimate>::value && has_fixed_size<sensor_msgs::msg::Image>::value> {};

template<>
struct has_bounded_size<cyberrunner_interfaces::msg::StateEstimateSub>
  : std::integral_constant<bool, has_bounded_size<cyberrunner_interfaces::msg::StateEstimate>::value && has_bounded_size<sensor_msgs::msg::Image>::value> {};

template<>
struct is_message<cyberrunner_interfaces::msg::StateEstimateSub>
  : std::true_type {};

}  // namespace rosidl_generator_traits

#endif  // CYBERRUNNER_INTERFACES__MSG__DETAIL__STATE_ESTIMATE_SUB__TRAITS_HPP_
