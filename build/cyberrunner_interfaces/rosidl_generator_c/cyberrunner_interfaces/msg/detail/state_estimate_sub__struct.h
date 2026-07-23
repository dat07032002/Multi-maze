// generated from rosidl_generator_c/resource/idl__struct.h.em
// with input from cyberrunner_interfaces:msg/StateEstimateSub.idl
// generated code does not contain a copyright notice

#ifndef CYBERRUNNER_INTERFACES__MSG__DETAIL__STATE_ESTIMATE_SUB__STRUCT_H_
#define CYBERRUNNER_INTERFACES__MSG__DETAIL__STATE_ESTIMATE_SUB__STRUCT_H_

#ifdef __cplusplus
extern "C"
{
#endif

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>


// Constants defined in the message

// Include directives for member types
// Member 'state'
#include "cyberrunner_interfaces/msg/detail/state_estimate__struct.h"
// Member 'subimg'
#include "sensor_msgs/msg/detail/image__struct.h"

/// Struct defined in msg/StateEstimateSub in the package cyberrunner_interfaces.
typedef struct cyberrunner_interfaces__msg__StateEstimateSub
{
  cyberrunner_interfaces__msg__StateEstimate state;
  sensor_msgs__msg__Image subimg;
} cyberrunner_interfaces__msg__StateEstimateSub;

// Struct for a sequence of cyberrunner_interfaces__msg__StateEstimateSub.
typedef struct cyberrunner_interfaces__msg__StateEstimateSub__Sequence
{
  cyberrunner_interfaces__msg__StateEstimateSub * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} cyberrunner_interfaces__msg__StateEstimateSub__Sequence;

#ifdef __cplusplus
}
#endif

#endif  // CYBERRUNNER_INTERFACES__MSG__DETAIL__STATE_ESTIMATE_SUB__STRUCT_H_
