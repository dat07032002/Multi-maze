// generated from rosidl_generator_cpp/resource/idl__traits.hpp.em
// with input from cyberrunner_interfaces:msg/DynamixelVel.idl
// generated code does not contain a copyright notice

#ifndef CYBERRUNNER_INTERFACES__MSG__DETAIL__DYNAMIXEL_VEL__TRAITS_HPP_
#define CYBERRUNNER_INTERFACES__MSG__DETAIL__DYNAMIXEL_VEL__TRAITS_HPP_

#include <stdint.h>

#include <sstream>
#include <string>
#include <type_traits>

#include "cyberrunner_interfaces/msg/detail/dynamixel_vel__struct.hpp"
#include "rosidl_runtime_cpp/traits.hpp"

namespace cyberrunner_interfaces
{

namespace msg
{

inline void to_flow_style_yaml(
  const DynamixelVel & msg,
  std::ostream & out)
{
  out << "{";
  // member: vel_1
  {
    out << "vel_1: ";
    rosidl_generator_traits::value_to_yaml(msg.vel_1, out);
    out << ", ";
  }

  // member: vel_2
  {
    out << "vel_2: ";
    rosidl_generator_traits::value_to_yaml(msg.vel_2, out);
  }
  out << "}";
}  // NOLINT(readability/fn_size)

inline void to_block_style_yaml(
  const DynamixelVel & msg,
  std::ostream & out, size_t indentation = 0)
{
  // member: vel_1
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "vel_1: ";
    rosidl_generator_traits::value_to_yaml(msg.vel_1, out);
    out << "\n";
  }

  // member: vel_2
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "vel_2: ";
    rosidl_generator_traits::value_to_yaml(msg.vel_2, out);
    out << "\n";
  }
}  // NOLINT(readability/fn_size)

inline std::string to_yaml(const DynamixelVel & msg, bool use_flow_style = false)
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
  const cyberrunner_interfaces::msg::DynamixelVel & msg,
  std::ostream & out, size_t indentation = 0)
{
  cyberrunner_interfaces::msg::to_block_style_yaml(msg, out, indentation);
}

[[deprecated("use cyberrunner_interfaces::msg::to_yaml() instead")]]
inline std::string to_yaml(const cyberrunner_interfaces::msg::DynamixelVel & msg)
{
  return cyberrunner_interfaces::msg::to_yaml(msg);
}

template<>
inline const char * data_type<cyberrunner_interfaces::msg::DynamixelVel>()
{
  return "cyberrunner_interfaces::msg::DynamixelVel";
}

template<>
inline const char * name<cyberrunner_interfaces::msg::DynamixelVel>()
{
  return "cyberrunner_interfaces/msg/DynamixelVel";
}

template<>
struct has_fixed_size<cyberrunner_interfaces::msg::DynamixelVel>
  : std::integral_constant<bool, true> {};

template<>
struct has_bounded_size<cyberrunner_interfaces::msg::DynamixelVel>
  : std::integral_constant<bool, true> {};

template<>
struct is_message<cyberrunner_interfaces::msg::DynamixelVel>
  : std::true_type {};

}  // namespace rosidl_generator_traits

#endif  // CYBERRUNNER_INTERFACES__MSG__DETAIL__DYNAMIXEL_VEL__TRAITS_HPP_
