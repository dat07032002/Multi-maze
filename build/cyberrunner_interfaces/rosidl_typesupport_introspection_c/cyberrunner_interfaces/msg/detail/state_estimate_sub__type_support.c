// generated from rosidl_typesupport_introspection_c/resource/idl__type_support.c.em
// with input from cyberrunner_interfaces:msg/StateEstimateSub.idl
// generated code does not contain a copyright notice

#include <stddef.h>
#include "cyberrunner_interfaces/msg/detail/state_estimate_sub__rosidl_typesupport_introspection_c.h"
#include "cyberrunner_interfaces/msg/rosidl_typesupport_introspection_c__visibility_control.h"
#include "rosidl_typesupport_introspection_c/field_types.h"
#include "rosidl_typesupport_introspection_c/identifier.h"
#include "rosidl_typesupport_introspection_c/message_introspection.h"
#include "cyberrunner_interfaces/msg/detail/state_estimate_sub__functions.h"
#include "cyberrunner_interfaces/msg/detail/state_estimate_sub__struct.h"


// Include directives for member types
// Member `state`
#include "cyberrunner_interfaces/msg/state_estimate.h"
// Member `state`
#include "cyberrunner_interfaces/msg/detail/state_estimate__rosidl_typesupport_introspection_c.h"
// Member `subimg`
#include "sensor_msgs/msg/image.h"
// Member `subimg`
#include "sensor_msgs/msg/detail/image__rosidl_typesupport_introspection_c.h"

#ifdef __cplusplus
extern "C"
{
#endif

void cyberrunner_interfaces__msg__StateEstimateSub__rosidl_typesupport_introspection_c__StateEstimateSub_init_function(
  void * message_memory, enum rosidl_runtime_c__message_initialization _init)
{
  // TODO(karsten1987): initializers are not yet implemented for typesupport c
  // see https://github.com/ros2/ros2/issues/397
  (void) _init;
  cyberrunner_interfaces__msg__StateEstimateSub__init(message_memory);
}

void cyberrunner_interfaces__msg__StateEstimateSub__rosidl_typesupport_introspection_c__StateEstimateSub_fini_function(void * message_memory)
{
  cyberrunner_interfaces__msg__StateEstimateSub__fini(message_memory);
}

static rosidl_typesupport_introspection_c__MessageMember cyberrunner_interfaces__msg__StateEstimateSub__rosidl_typesupport_introspection_c__StateEstimateSub_message_member_array[2] = {
  {
    "state",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_MESSAGE,  // type
    0,  // upper bound of string
    NULL,  // members of sub message (initialized later)
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(cyberrunner_interfaces__msg__StateEstimateSub, state),  // bytes offset in struct
    NULL,  // default value
    NULL,  // size() function pointer
    NULL,  // get_const(index) function pointer
    NULL,  // get(index) function pointer
    NULL,  // fetch(index, &value) function pointer
    NULL,  // assign(index, value) function pointer
    NULL  // resize(index) function pointer
  },
  {
    "subimg",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_MESSAGE,  // type
    0,  // upper bound of string
    NULL,  // members of sub message (initialized later)
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(cyberrunner_interfaces__msg__StateEstimateSub, subimg),  // bytes offset in struct
    NULL,  // default value
    NULL,  // size() function pointer
    NULL,  // get_const(index) function pointer
    NULL,  // get(index) function pointer
    NULL,  // fetch(index, &value) function pointer
    NULL,  // assign(index, value) function pointer
    NULL  // resize(index) function pointer
  }
};

static const rosidl_typesupport_introspection_c__MessageMembers cyberrunner_interfaces__msg__StateEstimateSub__rosidl_typesupport_introspection_c__StateEstimateSub_message_members = {
  "cyberrunner_interfaces__msg",  // message namespace
  "StateEstimateSub",  // message name
  2,  // number of fields
  sizeof(cyberrunner_interfaces__msg__StateEstimateSub),
  cyberrunner_interfaces__msg__StateEstimateSub__rosidl_typesupport_introspection_c__StateEstimateSub_message_member_array,  // message members
  cyberrunner_interfaces__msg__StateEstimateSub__rosidl_typesupport_introspection_c__StateEstimateSub_init_function,  // function to initialize message memory (memory has to be allocated)
  cyberrunner_interfaces__msg__StateEstimateSub__rosidl_typesupport_introspection_c__StateEstimateSub_fini_function  // function to terminate message instance (will not free memory)
};

// this is not const since it must be initialized on first access
// since C does not allow non-integral compile-time constants
static rosidl_message_type_support_t cyberrunner_interfaces__msg__StateEstimateSub__rosidl_typesupport_introspection_c__StateEstimateSub_message_type_support_handle = {
  0,
  &cyberrunner_interfaces__msg__StateEstimateSub__rosidl_typesupport_introspection_c__StateEstimateSub_message_members,
  get_message_typesupport_handle_function,
};

ROSIDL_TYPESUPPORT_INTROSPECTION_C_EXPORT_cyberrunner_interfaces
const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_c, cyberrunner_interfaces, msg, StateEstimateSub)() {
  cyberrunner_interfaces__msg__StateEstimateSub__rosidl_typesupport_introspection_c__StateEstimateSub_message_member_array[0].members_ =
    ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_c, cyberrunner_interfaces, msg, StateEstimate)();
  cyberrunner_interfaces__msg__StateEstimateSub__rosidl_typesupport_introspection_c__StateEstimateSub_message_member_array[1].members_ =
    ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_c, sensor_msgs, msg, Image)();
  if (!cyberrunner_interfaces__msg__StateEstimateSub__rosidl_typesupport_introspection_c__StateEstimateSub_message_type_support_handle.typesupport_identifier) {
    cyberrunner_interfaces__msg__StateEstimateSub__rosidl_typesupport_introspection_c__StateEstimateSub_message_type_support_handle.typesupport_identifier =
      rosidl_typesupport_introspection_c__identifier;
  }
  return &cyberrunner_interfaces__msg__StateEstimateSub__rosidl_typesupport_introspection_c__StateEstimateSub_message_type_support_handle;
}
#ifdef __cplusplus
}
#endif
