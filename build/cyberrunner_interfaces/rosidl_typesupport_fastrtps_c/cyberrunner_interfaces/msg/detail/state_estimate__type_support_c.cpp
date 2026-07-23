// generated from rosidl_typesupport_fastrtps_c/resource/idl__type_support_c.cpp.em
// with input from cyberrunner_interfaces:msg/StateEstimate.idl
// generated code does not contain a copyright notice
#include "cyberrunner_interfaces/msg/detail/state_estimate__rosidl_typesupport_fastrtps_c.h"


#include <cassert>
#include <limits>
#include <string>
#include "rosidl_typesupport_fastrtps_c/identifier.h"
#include "rosidl_typesupport_fastrtps_c/wstring_conversion.hpp"
#include "rosidl_typesupport_fastrtps_cpp/message_type_support.h"
#include "cyberrunner_interfaces/msg/rosidl_typesupport_fastrtps_c__visibility_control.h"
#include "cyberrunner_interfaces/msg/detail/state_estimate__struct.h"
#include "cyberrunner_interfaces/msg/detail/state_estimate__functions.h"
#include "fastcdr/Cdr.h"

#ifndef _WIN32
# pragma GCC diagnostic push
# pragma GCC diagnostic ignored "-Wunused-parameter"
# ifdef __clang__
#  pragma clang diagnostic ignored "-Wdeprecated-register"
#  pragma clang diagnostic ignored "-Wreturn-type-c-linkage"
# endif
#endif
#ifndef _WIN32
# pragma GCC diagnostic pop
#endif

// includes and forward declarations of message dependencies and their conversion functions

#if defined(__cplusplus)
extern "C"
{
#endif


// forward declare type support functions


using _StateEstimate__ros_msg_type = cyberrunner_interfaces__msg__StateEstimate;

static bool _StateEstimate__cdr_serialize(
  const void * untyped_ros_message,
  eprosima::fastcdr::Cdr & cdr)
{
  if (!untyped_ros_message) {
    fprintf(stderr, "ros message handle is null\n");
    return false;
  }
  const _StateEstimate__ros_msg_type * ros_message = static_cast<const _StateEstimate__ros_msg_type *>(untyped_ros_message);
  // Field name: x_b
  {
    cdr << ros_message->x_b;
  }

  // Field name: y_b
  {
    cdr << ros_message->y_b;
  }

  // Field name: x_b_dot
  {
    cdr << ros_message->x_b_dot;
  }

  // Field name: y_b_dot
  {
    cdr << ros_message->y_b_dot;
  }

  // Field name: alpha
  {
    cdr << ros_message->alpha;
  }

  // Field name: beta
  {
    cdr << ros_message->beta;
  }

  return true;
}

static bool _StateEstimate__cdr_deserialize(
  eprosima::fastcdr::Cdr & cdr,
  void * untyped_ros_message)
{
  if (!untyped_ros_message) {
    fprintf(stderr, "ros message handle is null\n");
    return false;
  }
  _StateEstimate__ros_msg_type * ros_message = static_cast<_StateEstimate__ros_msg_type *>(untyped_ros_message);
  // Field name: x_b
  {
    cdr >> ros_message->x_b;
  }

  // Field name: y_b
  {
    cdr >> ros_message->y_b;
  }

  // Field name: x_b_dot
  {
    cdr >> ros_message->x_b_dot;
  }

  // Field name: y_b_dot
  {
    cdr >> ros_message->y_b_dot;
  }

  // Field name: alpha
  {
    cdr >> ros_message->alpha;
  }

  // Field name: beta
  {
    cdr >> ros_message->beta;
  }

  return true;
}  // NOLINT(readability/fn_size)

ROSIDL_TYPESUPPORT_FASTRTPS_C_PUBLIC_cyberrunner_interfaces
size_t get_serialized_size_cyberrunner_interfaces__msg__StateEstimate(
  const void * untyped_ros_message,
  size_t current_alignment)
{
  const _StateEstimate__ros_msg_type * ros_message = static_cast<const _StateEstimate__ros_msg_type *>(untyped_ros_message);
  (void)ros_message;
  size_t initial_alignment = current_alignment;

  const size_t padding = 4;
  const size_t wchar_size = 4;
  (void)padding;
  (void)wchar_size;

  // field.name x_b
  {
    size_t item_size = sizeof(ros_message->x_b);
    current_alignment += item_size +
      eprosima::fastcdr::Cdr::alignment(current_alignment, item_size);
  }
  // field.name y_b
  {
    size_t item_size = sizeof(ros_message->y_b);
    current_alignment += item_size +
      eprosima::fastcdr::Cdr::alignment(current_alignment, item_size);
  }
  // field.name x_b_dot
  {
    size_t item_size = sizeof(ros_message->x_b_dot);
    current_alignment += item_size +
      eprosima::fastcdr::Cdr::alignment(current_alignment, item_size);
  }
  // field.name y_b_dot
  {
    size_t item_size = sizeof(ros_message->y_b_dot);
    current_alignment += item_size +
      eprosima::fastcdr::Cdr::alignment(current_alignment, item_size);
  }
  // field.name alpha
  {
    size_t item_size = sizeof(ros_message->alpha);
    current_alignment += item_size +
      eprosima::fastcdr::Cdr::alignment(current_alignment, item_size);
  }
  // field.name beta
  {
    size_t item_size = sizeof(ros_message->beta);
    current_alignment += item_size +
      eprosima::fastcdr::Cdr::alignment(current_alignment, item_size);
  }

  return current_alignment - initial_alignment;
}

static uint32_t _StateEstimate__get_serialized_size(const void * untyped_ros_message)
{
  return static_cast<uint32_t>(
    get_serialized_size_cyberrunner_interfaces__msg__StateEstimate(
      untyped_ros_message, 0));
}

ROSIDL_TYPESUPPORT_FASTRTPS_C_PUBLIC_cyberrunner_interfaces
size_t max_serialized_size_cyberrunner_interfaces__msg__StateEstimate(
  bool & full_bounded,
  bool & is_plain,
  size_t current_alignment)
{
  size_t initial_alignment = current_alignment;

  const size_t padding = 4;
  const size_t wchar_size = 4;
  size_t last_member_size = 0;
  (void)last_member_size;
  (void)padding;
  (void)wchar_size;

  full_bounded = true;
  is_plain = true;

  // member: x_b
  {
    size_t array_size = 1;

    last_member_size = array_size * sizeof(uint64_t);
    current_alignment += array_size * sizeof(uint64_t) +
      eprosima::fastcdr::Cdr::alignment(current_alignment, sizeof(uint64_t));
  }
  // member: y_b
  {
    size_t array_size = 1;

    last_member_size = array_size * sizeof(uint64_t);
    current_alignment += array_size * sizeof(uint64_t) +
      eprosima::fastcdr::Cdr::alignment(current_alignment, sizeof(uint64_t));
  }
  // member: x_b_dot
  {
    size_t array_size = 1;

    last_member_size = array_size * sizeof(uint64_t);
    current_alignment += array_size * sizeof(uint64_t) +
      eprosima::fastcdr::Cdr::alignment(current_alignment, sizeof(uint64_t));
  }
  // member: y_b_dot
  {
    size_t array_size = 1;

    last_member_size = array_size * sizeof(uint64_t);
    current_alignment += array_size * sizeof(uint64_t) +
      eprosima::fastcdr::Cdr::alignment(current_alignment, sizeof(uint64_t));
  }
  // member: alpha
  {
    size_t array_size = 1;

    last_member_size = array_size * sizeof(uint64_t);
    current_alignment += array_size * sizeof(uint64_t) +
      eprosima::fastcdr::Cdr::alignment(current_alignment, sizeof(uint64_t));
  }
  // member: beta
  {
    size_t array_size = 1;

    last_member_size = array_size * sizeof(uint64_t);
    current_alignment += array_size * sizeof(uint64_t) +
      eprosima::fastcdr::Cdr::alignment(current_alignment, sizeof(uint64_t));
  }

  size_t ret_val = current_alignment - initial_alignment;
  if (is_plain) {
    // All members are plain, and type is not empty.
    // We still need to check that the in-memory alignment
    // is the same as the CDR mandated alignment.
    using DataType = cyberrunner_interfaces__msg__StateEstimate;
    is_plain =
      (
      offsetof(DataType, beta) +
      last_member_size
      ) == ret_val;
  }

  return ret_val;
}

static size_t _StateEstimate__max_serialized_size(char & bounds_info)
{
  bool full_bounded;
  bool is_plain;
  size_t ret_val;

  ret_val = max_serialized_size_cyberrunner_interfaces__msg__StateEstimate(
    full_bounded, is_plain, 0);

  bounds_info =
    is_plain ? ROSIDL_TYPESUPPORT_FASTRTPS_PLAIN_TYPE :
    full_bounded ? ROSIDL_TYPESUPPORT_FASTRTPS_BOUNDED_TYPE : ROSIDL_TYPESUPPORT_FASTRTPS_UNBOUNDED_TYPE;
  return ret_val;
}


static message_type_support_callbacks_t __callbacks_StateEstimate = {
  "cyberrunner_interfaces::msg",
  "StateEstimate",
  _StateEstimate__cdr_serialize,
  _StateEstimate__cdr_deserialize,
  _StateEstimate__get_serialized_size,
  _StateEstimate__max_serialized_size
};

static rosidl_message_type_support_t _StateEstimate__type_support = {
  rosidl_typesupport_fastrtps_c__identifier,
  &__callbacks_StateEstimate,
  get_message_typesupport_handle_function,
};

const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_fastrtps_c, cyberrunner_interfaces, msg, StateEstimate)() {
  return &_StateEstimate__type_support;
}

#if defined(__cplusplus)
}
#endif
