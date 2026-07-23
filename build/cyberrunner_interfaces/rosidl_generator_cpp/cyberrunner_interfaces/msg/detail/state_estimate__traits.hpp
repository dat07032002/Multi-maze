// generated from rosidl_generator_cpp/resource/idl__traits.hpp.em
// with input from cyberrunner_interfaces:msg/StateEstimate.idl
// generated code does not contain a copyright notice

#ifndef CYBERRUNNER_INTERFACES__MSG__DETAIL__STATE_ESTIMATE__TRAITS_HPP_
#define CYBERRUNNER_INTERFACES__MSG__DETAIL__STATE_ESTIMATE__TRAITS_HPP_

#include <stdint.h>

#include <sstream>
#include <string>
#include <type_traits>

#include "cyberrunner_interfaces/msg/detail/state_estimate__struct.hpp"
#include "rosidl_runtime_cpp/traits.hpp"

namespace cyberrunner_interfaces
{

namespace msg
{

inline void to_flow_style_yaml(
  const StateEstimate & msg,
  std::ostream & out)
{
  out << "{";
  // member: x_b
  {
    out << "x_b: ";
    rosidl_generator_traits::value_to_yaml(msg.x_b, out);
    out << ", ";
  }

  // member: y_b
  {
    out << "y_b: ";
    rosidl_generator_traits::value_to_yaml(msg.y_b, out);
    out << ", ";
  }

  // member: x_b_dot
  {
    out << "x_b_dot: ";
    rosidl_generator_traits::value_to_yaml(msg.x_b_dot, out);
    out << ", ";
  }

  // member: y_b_dot
  {
    out << "y_b_dot: ";
    rosidl_generator_traits::value_to_yaml(msg.y_b_dot, out);
    out << ", ";
  }

  // member: alpha
  {
    out << "alpha: ";
    rosidl_generator_traits::value_to_yaml(msg.alpha, out);
    out << ", ";
  }

  // member: beta
  {
    out << "beta: ";
    rosidl_generator_traits::value_to_yaml(msg.beta, out);
  }
  out << "}";
}  // NOLINT(readability/fn_size)

inline void to_block_style_yaml(
  const StateEstimate & msg,
  std::ostream & out, size_t indentation = 0)
{
  // member: x_b
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "x_b: ";
    rosidl_generator_traits::value_to_yaml(msg.x_b, out);
    out << "\n";
  }

  // member: y_b
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "y_b: ";
    rosidl_generator_traits::value_to_yaml(msg.y_b, out);
    out << "\n";
  }

  // member: x_b_dot
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "x_b_dot: ";
    rosidl_generator_traits::value_to_yaml(msg.x_b_dot, out);
    out << "\n";
  }

  // member: y_b_dot
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "y_b_dot: ";
    rosidl_generator_traits::value_to_yaml(msg.y_b_dot, out);
    out << "\n";
  }

  // member: alpha
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "alpha: ";
    rosidl_generator_traits::value_to_yaml(msg.alpha, out);
    out << "\n";
  }

  // member: beta
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "beta: ";
    rosidl_generator_traits::value_to_yaml(msg.beta, out);
    out << "\n";
  }
}  // NOLINT(readability/fn_size)

inline std::string to_yaml(const StateEstimate & msg, bool use_flow_style = false)
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
  const cyberrunner_interfaces::msg::StateEstimate & msg,
  std::ostream & out, size_t indentation = 0)
{
  cyberrunner_interfaces::msg::to_block_style_yaml(msg, out, indentation);
}

[[deprecated("use cyberrunner_interfaces::msg::to_yaml() instead")]]
inline std::string to_yaml(const cyberrunner_interfaces::msg::StateEstimate & msg)
{
  return cyberrunner_interfaces::msg::to_yaml(msg);
}

template<>
inline const char * data_type<cyberrunner_interfaces::msg::StateEstimate>()
{
  return "cyberrunner_interfaces::msg::StateEstimate";
}

template<>
inline const char * name<cyberrunner_interfaces::msg::StateEstimate>()
{
  return "cyberrunner_interfaces/msg/StateEstimate";
}

template<>
struct has_fixed_size<cyberrunner_interfaces::msg::StateEstimate>
  : std::integral_constant<bool, true> {};

template<>
struct has_bounded_size<cyberrunner_interfaces::msg::StateEstimate>
  : std::integral_constant<bool, true> {};

template<>
struct is_message<cyberrunner_interfaces::msg::StateEstimate>
  : std::true_type {};

}  // namespace rosidl_generator_traits

#endif  // CYBERRUNNER_INTERFACES__MSG__DETAIL__STATE_ESTIMATE__TRAITS_HPP_
