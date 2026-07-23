// generated from rosidl_generator_cpp/resource/idl__traits.hpp.em
// with input from cyberrunner_interfaces:srv/DynamixelReset.idl
// generated code does not contain a copyright notice

#ifndef CYBERRUNNER_INTERFACES__SRV__DETAIL__DYNAMIXEL_RESET__TRAITS_HPP_
#define CYBERRUNNER_INTERFACES__SRV__DETAIL__DYNAMIXEL_RESET__TRAITS_HPP_

#include <stdint.h>

#include <sstream>
#include <string>
#include <type_traits>

#include "cyberrunner_interfaces/srv/detail/dynamixel_reset__struct.hpp"
#include "rosidl_runtime_cpp/traits.hpp"

namespace cyberrunner_interfaces
{

namespace srv
{

inline void to_flow_style_yaml(
  const DynamixelReset_Request & msg,
  std::ostream & out)
{
  out << "{";
  // member: max_temp
  {
    out << "max_temp: ";
    rosidl_generator_traits::value_to_yaml(msg.max_temp, out);
  }
  out << "}";
}  // NOLINT(readability/fn_size)

inline void to_block_style_yaml(
  const DynamixelReset_Request & msg,
  std::ostream & out, size_t indentation = 0)
{
  // member: max_temp
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "max_temp: ";
    rosidl_generator_traits::value_to_yaml(msg.max_temp, out);
    out << "\n";
  }
}  // NOLINT(readability/fn_size)

inline std::string to_yaml(const DynamixelReset_Request & msg, bool use_flow_style = false)
{
  std::ostringstream out;
  if (use_flow_style) {
    to_flow_style_yaml(msg, out);
  } else {
    to_block_style_yaml(msg, out);
  }
  return out.str();
}

}  // namespace srv

}  // namespace cyberrunner_interfaces

namespace rosidl_generator_traits
{

[[deprecated("use cyberrunner_interfaces::srv::to_block_style_yaml() instead")]]
inline void to_yaml(
  const cyberrunner_interfaces::srv::DynamixelReset_Request & msg,
  std::ostream & out, size_t indentation = 0)
{
  cyberrunner_interfaces::srv::to_block_style_yaml(msg, out, indentation);
}

[[deprecated("use cyberrunner_interfaces::srv::to_yaml() instead")]]
inline std::string to_yaml(const cyberrunner_interfaces::srv::DynamixelReset_Request & msg)
{
  return cyberrunner_interfaces::srv::to_yaml(msg);
}

template<>
inline const char * data_type<cyberrunner_interfaces::srv::DynamixelReset_Request>()
{
  return "cyberrunner_interfaces::srv::DynamixelReset_Request";
}

template<>
inline const char * name<cyberrunner_interfaces::srv::DynamixelReset_Request>()
{
  return "cyberrunner_interfaces/srv/DynamixelReset_Request";
}

template<>
struct has_fixed_size<cyberrunner_interfaces::srv::DynamixelReset_Request>
  : std::integral_constant<bool, true> {};

template<>
struct has_bounded_size<cyberrunner_interfaces::srv::DynamixelReset_Request>
  : std::integral_constant<bool, true> {};

template<>
struct is_message<cyberrunner_interfaces::srv::DynamixelReset_Request>
  : std::true_type {};

}  // namespace rosidl_generator_traits

namespace cyberrunner_interfaces
{

namespace srv
{

inline void to_flow_style_yaml(
  const DynamixelReset_Response & msg,
  std::ostream & out)
{
  out << "{";
  // member: success
  {
    out << "success: ";
    rosidl_generator_traits::value_to_yaml(msg.success, out);
  }
  out << "}";
}  // NOLINT(readability/fn_size)

inline void to_block_style_yaml(
  const DynamixelReset_Response & msg,
  std::ostream & out, size_t indentation = 0)
{
  // member: success
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "success: ";
    rosidl_generator_traits::value_to_yaml(msg.success, out);
    out << "\n";
  }
}  // NOLINT(readability/fn_size)

inline std::string to_yaml(const DynamixelReset_Response & msg, bool use_flow_style = false)
{
  std::ostringstream out;
  if (use_flow_style) {
    to_flow_style_yaml(msg, out);
  } else {
    to_block_style_yaml(msg, out);
  }
  return out.str();
}

}  // namespace srv

}  // namespace cyberrunner_interfaces

namespace rosidl_generator_traits
{

[[deprecated("use cyberrunner_interfaces::srv::to_block_style_yaml() instead")]]
inline void to_yaml(
  const cyberrunner_interfaces::srv::DynamixelReset_Response & msg,
  std::ostream & out, size_t indentation = 0)
{
  cyberrunner_interfaces::srv::to_block_style_yaml(msg, out, indentation);
}

[[deprecated("use cyberrunner_interfaces::srv::to_yaml() instead")]]
inline std::string to_yaml(const cyberrunner_interfaces::srv::DynamixelReset_Response & msg)
{
  return cyberrunner_interfaces::srv::to_yaml(msg);
}

template<>
inline const char * data_type<cyberrunner_interfaces::srv::DynamixelReset_Response>()
{
  return "cyberrunner_interfaces::srv::DynamixelReset_Response";
}

template<>
inline const char * name<cyberrunner_interfaces::srv::DynamixelReset_Response>()
{
  return "cyberrunner_interfaces/srv/DynamixelReset_Response";
}

template<>
struct has_fixed_size<cyberrunner_interfaces::srv::DynamixelReset_Response>
  : std::integral_constant<bool, true> {};

template<>
struct has_bounded_size<cyberrunner_interfaces::srv::DynamixelReset_Response>
  : std::integral_constant<bool, true> {};

template<>
struct is_message<cyberrunner_interfaces::srv::DynamixelReset_Response>
  : std::true_type {};

}  // namespace rosidl_generator_traits

namespace rosidl_generator_traits
{

template<>
inline const char * data_type<cyberrunner_interfaces::srv::DynamixelReset>()
{
  return "cyberrunner_interfaces::srv::DynamixelReset";
}

template<>
inline const char * name<cyberrunner_interfaces::srv::DynamixelReset>()
{
  return "cyberrunner_interfaces/srv/DynamixelReset";
}

template<>
struct has_fixed_size<cyberrunner_interfaces::srv::DynamixelReset>
  : std::integral_constant<
    bool,
    has_fixed_size<cyberrunner_interfaces::srv::DynamixelReset_Request>::value &&
    has_fixed_size<cyberrunner_interfaces::srv::DynamixelReset_Response>::value
  >
{
};

template<>
struct has_bounded_size<cyberrunner_interfaces::srv::DynamixelReset>
  : std::integral_constant<
    bool,
    has_bounded_size<cyberrunner_interfaces::srv::DynamixelReset_Request>::value &&
    has_bounded_size<cyberrunner_interfaces::srv::DynamixelReset_Response>::value
  >
{
};

template<>
struct is_service<cyberrunner_interfaces::srv::DynamixelReset>
  : std::true_type
{
};

template<>
struct is_service_request<cyberrunner_interfaces::srv::DynamixelReset_Request>
  : std::true_type
{
};

template<>
struct is_service_response<cyberrunner_interfaces::srv::DynamixelReset_Response>
  : std::true_type
{
};

}  // namespace rosidl_generator_traits

#endif  // CYBERRUNNER_INTERFACES__SRV__DETAIL__DYNAMIXEL_RESET__TRAITS_HPP_
