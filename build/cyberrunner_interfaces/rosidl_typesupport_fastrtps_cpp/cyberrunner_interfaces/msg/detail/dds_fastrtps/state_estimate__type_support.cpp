// generated from rosidl_typesupport_fastrtps_cpp/resource/idl__type_support.cpp.em
// with input from cyberrunner_interfaces:msg/StateEstimate.idl
// generated code does not contain a copyright notice
#include "cyberrunner_interfaces/msg/detail/state_estimate__rosidl_typesupport_fastrtps_cpp.hpp"
#include "cyberrunner_interfaces/msg/detail/state_estimate__struct.hpp"

#include <limits>
#include <stdexcept>
#include <string>
#include "rosidl_typesupport_cpp/message_type_support.hpp"
#include "rosidl_typesupport_fastrtps_cpp/identifier.hpp"
#include "rosidl_typesupport_fastrtps_cpp/message_type_support.h"
#include "rosidl_typesupport_fastrtps_cpp/message_type_support_decl.hpp"
#include "rosidl_typesupport_fastrtps_cpp/wstring_conversion.hpp"
#include "fastcdr/Cdr.h"


// forward declaration of message dependencies and their conversion functions

namespace cyberrunner_interfaces
{

namespace msg
{

namespace typesupport_fastrtps_cpp
{

bool
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_cyberrunner_interfaces
cdr_serialize(
  const cyberrunner_interfaces::msg::StateEstimate & ros_message,
  eprosima::fastcdr::Cdr & cdr)
{
  // Member: x_b
  cdr << ros_message.x_b;
  // Member: y_b
  cdr << ros_message.y_b;
  // Member: x_b_dot
  cdr << ros_message.x_b_dot;
  // Member: y_b_dot
  cdr << ros_message.y_b_dot;
  // Member: alpha
  cdr << ros_message.alpha;
  // Member: beta
  cdr << ros_message.beta;
  return true;
}

bool
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_cyberrunner_interfaces
cdr_deserialize(
  eprosima::fastcdr::Cdr & cdr,
  cyberrunner_interfaces::msg::StateEstimate & ros_message)
{
  // Member: x_b
  cdr >> ros_message.x_b;

  // Member: y_b
  cdr >> ros_message.y_b;

  // Member: x_b_dot
  cdr >> ros_message.x_b_dot;

  // Member: y_b_dot
  cdr >> ros_message.y_b_dot;

  // Member: alpha
  cdr >> ros_message.alpha;

  // Member: beta
  cdr >> ros_message.beta;

  return true;
}  // NOLINT(readability/fn_size)

size_t
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_cyberrunner_interfaces
get_serialized_size(
  const cyberrunner_interfaces::msg::StateEstimate & ros_message,
  size_t current_alignment)
{
  size_t initial_alignment = current_alignment;

  const size_t padding = 4;
  const size_t wchar_size = 4;
  (void)padding;
  (void)wchar_size;

  // Member: x_b
  {
    size_t item_size = sizeof(ros_message.x_b);
    current_alignment += item_size +
      eprosima::fastcdr::Cdr::alignment(current_alignment, item_size);
  }
  // Member: y_b
  {
    size_t item_size = sizeof(ros_message.y_b);
    current_alignment += item_size +
      eprosima::fastcdr::Cdr::alignment(current_alignment, item_size);
  }
  // Member: x_b_dot
  {
    size_t item_size = sizeof(ros_message.x_b_dot);
    current_alignment += item_size +
      eprosima::fastcdr::Cdr::alignment(current_alignment, item_size);
  }
  // Member: y_b_dot
  {
    size_t item_size = sizeof(ros_message.y_b_dot);
    current_alignment += item_size +
      eprosima::fastcdr::Cdr::alignment(current_alignment, item_size);
  }
  // Member: alpha
  {
    size_t item_size = sizeof(ros_message.alpha);
    current_alignment += item_size +
      eprosima::fastcdr::Cdr::alignment(current_alignment, item_size);
  }
  // Member: beta
  {
    size_t item_size = sizeof(ros_message.beta);
    current_alignment += item_size +
      eprosima::fastcdr::Cdr::alignment(current_alignment, item_size);
  }

  return current_alignment - initial_alignment;
}

size_t
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_cyberrunner_interfaces
max_serialized_size_StateEstimate(
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


  // Member: x_b
  {
    size_t array_size = 1;

    last_member_size = array_size * sizeof(uint64_t);
    current_alignment += array_size * sizeof(uint64_t) +
      eprosima::fastcdr::Cdr::alignment(current_alignment, sizeof(uint64_t));
  }

  // Member: y_b
  {
    size_t array_size = 1;

    last_member_size = array_size * sizeof(uint64_t);
    current_alignment += array_size * sizeof(uint64_t) +
      eprosima::fastcdr::Cdr::alignment(current_alignment, sizeof(uint64_t));
  }

  // Member: x_b_dot
  {
    size_t array_size = 1;

    last_member_size = array_size * sizeof(uint64_t);
    current_alignment += array_size * sizeof(uint64_t) +
      eprosima::fastcdr::Cdr::alignment(current_alignment, sizeof(uint64_t));
  }

  // Member: y_b_dot
  {
    size_t array_size = 1;

    last_member_size = array_size * sizeof(uint64_t);
    current_alignment += array_size * sizeof(uint64_t) +
      eprosima::fastcdr::Cdr::alignment(current_alignment, sizeof(uint64_t));
  }

  // Member: alpha
  {
    size_t array_size = 1;

    last_member_size = array_size * sizeof(uint64_t);
    current_alignment += array_size * sizeof(uint64_t) +
      eprosima::fastcdr::Cdr::alignment(current_alignment, sizeof(uint64_t));
  }

  // Member: beta
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
    using DataType = cyberrunner_interfaces::msg::StateEstimate;
    is_plain =
      (
      offsetof(DataType, beta) +
      last_member_size
      ) == ret_val;
  }

  return ret_val;
}

static bool _StateEstimate__cdr_serialize(
  const void * untyped_ros_message,
  eprosima::fastcdr::Cdr & cdr)
{
  auto typed_message =
    static_cast<const cyberrunner_interfaces::msg::StateEstimate *>(
    untyped_ros_message);
  return cdr_serialize(*typed_message, cdr);
}

static bool _StateEstimate__cdr_deserialize(
  eprosima::fastcdr::Cdr & cdr,
  void * untyped_ros_message)
{
  auto typed_message =
    static_cast<cyberrunner_interfaces::msg::StateEstimate *>(
    untyped_ros_message);
  return cdr_deserialize(cdr, *typed_message);
}

static uint32_t _StateEstimate__get_serialized_size(
  const void * untyped_ros_message)
{
  auto typed_message =
    static_cast<const cyberrunner_interfaces::msg::StateEstimate *>(
    untyped_ros_message);
  return static_cast<uint32_t>(get_serialized_size(*typed_message, 0));
}

static size_t _StateEstimate__max_serialized_size(char & bounds_info)
{
  bool full_bounded;
  bool is_plain;
  size_t ret_val;

  ret_val = max_serialized_size_StateEstimate(full_bounded, is_plain, 0);

  bounds_info =
    is_plain ? ROSIDL_TYPESUPPORT_FASTRTPS_PLAIN_TYPE :
    full_bounded ? ROSIDL_TYPESUPPORT_FASTRTPS_BOUNDED_TYPE : ROSIDL_TYPESUPPORT_FASTRTPS_UNBOUNDED_TYPE;
  return ret_val;
}

static message_type_support_callbacks_t _StateEstimate__callbacks = {
  "cyberrunner_interfaces::msg",
  "StateEstimate",
  _StateEstimate__cdr_serialize,
  _StateEstimate__cdr_deserialize,
  _StateEstimate__get_serialized_size,
  _StateEstimate__max_serialized_size
};

static rosidl_message_type_support_t _StateEstimate__handle = {
  rosidl_typesupport_fastrtps_cpp::typesupport_identifier,
  &_StateEstimate__callbacks,
  get_message_typesupport_handle_function,
};

}  // namespace typesupport_fastrtps_cpp

}  // namespace msg

}  // namespace cyberrunner_interfaces

namespace rosidl_typesupport_fastrtps_cpp
{

template<>
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_EXPORT_cyberrunner_interfaces
const rosidl_message_type_support_t *
get_message_type_support_handle<cyberrunner_interfaces::msg::StateEstimate>()
{
  return &cyberrunner_interfaces::msg::typesupport_fastrtps_cpp::_StateEstimate__handle;
}

}  // namespace rosidl_typesupport_fastrtps_cpp

#ifdef __cplusplus
extern "C"
{
#endif

const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_fastrtps_cpp, cyberrunner_interfaces, msg, StateEstimate)() {
  return &cyberrunner_interfaces::msg::typesupport_fastrtps_cpp::_StateEstimate__handle;
}

#ifdef __cplusplus
}
#endif
