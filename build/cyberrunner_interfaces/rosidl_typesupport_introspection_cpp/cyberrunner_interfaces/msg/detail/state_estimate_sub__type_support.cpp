// generated from rosidl_typesupport_introspection_cpp/resource/idl__type_support.cpp.em
// with input from cyberrunner_interfaces:msg/StateEstimateSub.idl
// generated code does not contain a copyright notice

#include "array"
#include "cstddef"
#include "string"
#include "vector"
#include "rosidl_runtime_c/message_type_support_struct.h"
#include "rosidl_typesupport_cpp/message_type_support.hpp"
#include "rosidl_typesupport_interface/macros.h"
#include "cyberrunner_interfaces/msg/detail/state_estimate_sub__struct.hpp"
#include "rosidl_typesupport_introspection_cpp/field_types.hpp"
#include "rosidl_typesupport_introspection_cpp/identifier.hpp"
#include "rosidl_typesupport_introspection_cpp/message_introspection.hpp"
#include "rosidl_typesupport_introspection_cpp/message_type_support_decl.hpp"
#include "rosidl_typesupport_introspection_cpp/visibility_control.h"

namespace cyberrunner_interfaces
{

namespace msg
{

namespace rosidl_typesupport_introspection_cpp
{

void StateEstimateSub_init_function(
  void * message_memory, rosidl_runtime_cpp::MessageInitialization _init)
{
  new (message_memory) cyberrunner_interfaces::msg::StateEstimateSub(_init);
}

void StateEstimateSub_fini_function(void * message_memory)
{
  auto typed_message = static_cast<cyberrunner_interfaces::msg::StateEstimateSub *>(message_memory);
  typed_message->~StateEstimateSub();
}

static const ::rosidl_typesupport_introspection_cpp::MessageMember StateEstimateSub_message_member_array[2] = {
  {
    "state",  // name
    ::rosidl_typesupport_introspection_cpp::ROS_TYPE_MESSAGE,  // type
    0,  // upper bound of string
    ::rosidl_typesupport_introspection_cpp::get_message_type_support_handle<cyberrunner_interfaces::msg::StateEstimate>(),  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(cyberrunner_interfaces::msg::StateEstimateSub, state),  // bytes offset in struct
    nullptr,  // default value
    nullptr,  // size() function pointer
    nullptr,  // get_const(index) function pointer
    nullptr,  // get(index) function pointer
    nullptr,  // fetch(index, &value) function pointer
    nullptr,  // assign(index, value) function pointer
    nullptr  // resize(index) function pointer
  },
  {
    "subimg",  // name
    ::rosidl_typesupport_introspection_cpp::ROS_TYPE_MESSAGE,  // type
    0,  // upper bound of string
    ::rosidl_typesupport_introspection_cpp::get_message_type_support_handle<sensor_msgs::msg::Image>(),  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(cyberrunner_interfaces::msg::StateEstimateSub, subimg),  // bytes offset in struct
    nullptr,  // default value
    nullptr,  // size() function pointer
    nullptr,  // get_const(index) function pointer
    nullptr,  // get(index) function pointer
    nullptr,  // fetch(index, &value) function pointer
    nullptr,  // assign(index, value) function pointer
    nullptr  // resize(index) function pointer
  }
};

static const ::rosidl_typesupport_introspection_cpp::MessageMembers StateEstimateSub_message_members = {
  "cyberrunner_interfaces::msg",  // message namespace
  "StateEstimateSub",  // message name
  2,  // number of fields
  sizeof(cyberrunner_interfaces::msg::StateEstimateSub),
  StateEstimateSub_message_member_array,  // message members
  StateEstimateSub_init_function,  // function to initialize message memory (memory has to be allocated)
  StateEstimateSub_fini_function  // function to terminate message instance (will not free memory)
};

static const rosidl_message_type_support_t StateEstimateSub_message_type_support_handle = {
  ::rosidl_typesupport_introspection_cpp::typesupport_identifier,
  &StateEstimateSub_message_members,
  get_message_typesupport_handle_function,
};

}  // namespace rosidl_typesupport_introspection_cpp

}  // namespace msg

}  // namespace cyberrunner_interfaces


namespace rosidl_typesupport_introspection_cpp
{

template<>
ROSIDL_TYPESUPPORT_INTROSPECTION_CPP_PUBLIC
const rosidl_message_type_support_t *
get_message_type_support_handle<cyberrunner_interfaces::msg::StateEstimateSub>()
{
  return &::cyberrunner_interfaces::msg::rosidl_typesupport_introspection_cpp::StateEstimateSub_message_type_support_handle;
}

}  // namespace rosidl_typesupport_introspection_cpp

#ifdef __cplusplus
extern "C"
{
#endif

ROSIDL_TYPESUPPORT_INTROSPECTION_CPP_PUBLIC
const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_cpp, cyberrunner_interfaces, msg, StateEstimateSub)() {
  return &::cyberrunner_interfaces::msg::rosidl_typesupport_introspection_cpp::StateEstimateSub_message_type_support_handle;
}

#ifdef __cplusplus
}
#endif
