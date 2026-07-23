// generated from rosidl_generator_c/resource/idl__struct.h.em
// with input from cyberrunner_interfaces:srv/DynamixelReset.idl
// generated code does not contain a copyright notice

#ifndef CYBERRUNNER_INTERFACES__SRV__DETAIL__DYNAMIXEL_RESET__STRUCT_H_
#define CYBERRUNNER_INTERFACES__SRV__DETAIL__DYNAMIXEL_RESET__STRUCT_H_

#ifdef __cplusplus
extern "C"
{
#endif

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>


// Constants defined in the message

/// Struct defined in srv/DynamixelReset in the package cyberrunner_interfaces.
typedef struct cyberrunner_interfaces__srv__DynamixelReset_Request
{
  uint16_t max_temp;
} cyberrunner_interfaces__srv__DynamixelReset_Request;

// Struct for a sequence of cyberrunner_interfaces__srv__DynamixelReset_Request.
typedef struct cyberrunner_interfaces__srv__DynamixelReset_Request__Sequence
{
  cyberrunner_interfaces__srv__DynamixelReset_Request * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} cyberrunner_interfaces__srv__DynamixelReset_Request__Sequence;


// Constants defined in the message

/// Struct defined in srv/DynamixelReset in the package cyberrunner_interfaces.
typedef struct cyberrunner_interfaces__srv__DynamixelReset_Response
{
  int8_t success;
} cyberrunner_interfaces__srv__DynamixelReset_Response;

// Struct for a sequence of cyberrunner_interfaces__srv__DynamixelReset_Response.
typedef struct cyberrunner_interfaces__srv__DynamixelReset_Response__Sequence
{
  cyberrunner_interfaces__srv__DynamixelReset_Response * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} cyberrunner_interfaces__srv__DynamixelReset_Response__Sequence;

#ifdef __cplusplus
}
#endif

#endif  // CYBERRUNNER_INTERFACES__SRV__DETAIL__DYNAMIXEL_RESET__STRUCT_H_
