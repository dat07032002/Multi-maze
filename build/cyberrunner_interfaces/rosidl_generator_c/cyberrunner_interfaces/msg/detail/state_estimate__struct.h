// generated from rosidl_generator_c/resource/idl__struct.h.em
// with input from cyberrunner_interfaces:msg/StateEstimate.idl
// generated code does not contain a copyright notice

#ifndef CYBERRUNNER_INTERFACES__MSG__DETAIL__STATE_ESTIMATE__STRUCT_H_
#define CYBERRUNNER_INTERFACES__MSG__DETAIL__STATE_ESTIMATE__STRUCT_H_

#ifdef __cplusplus
extern "C"
{
#endif

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>


// Constants defined in the message

/// Struct defined in msg/StateEstimate in the package cyberrunner_interfaces.
typedef struct cyberrunner_interfaces__msg__StateEstimate
{
  double x_b;
  double y_b;
  double x_b_dot;
  double y_b_dot;
  double alpha;
  double beta;
} cyberrunner_interfaces__msg__StateEstimate;

// Struct for a sequence of cyberrunner_interfaces__msg__StateEstimate.
typedef struct cyberrunner_interfaces__msg__StateEstimate__Sequence
{
  cyberrunner_interfaces__msg__StateEstimate * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} cyberrunner_interfaces__msg__StateEstimate__Sequence;

#ifdef __cplusplus
}
#endif

#endif  // CYBERRUNNER_INTERFACES__MSG__DETAIL__STATE_ESTIMATE__STRUCT_H_
