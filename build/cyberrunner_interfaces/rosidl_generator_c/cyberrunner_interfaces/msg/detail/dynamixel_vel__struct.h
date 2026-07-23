// generated from rosidl_generator_c/resource/idl__struct.h.em
// with input from cyberrunner_interfaces:msg/DynamixelVel.idl
// generated code does not contain a copyright notice

#ifndef CYBERRUNNER_INTERFACES__MSG__DETAIL__DYNAMIXEL_VEL__STRUCT_H_
#define CYBERRUNNER_INTERFACES__MSG__DETAIL__DYNAMIXEL_VEL__STRUCT_H_

#ifdef __cplusplus
extern "C"
{
#endif

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>


// Constants defined in the message

/// Struct defined in msg/DynamixelVel in the package cyberrunner_interfaces.
/**
  * Velocity commands for the dynamixels  TODO: refactor
 */
typedef struct cyberrunner_interfaces__msg__DynamixelVel
{
  double vel_1;
  double vel_2;
} cyberrunner_interfaces__msg__DynamixelVel;

// Struct for a sequence of cyberrunner_interfaces__msg__DynamixelVel.
typedef struct cyberrunner_interfaces__msg__DynamixelVel__Sequence
{
  cyberrunner_interfaces__msg__DynamixelVel * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} cyberrunner_interfaces__msg__DynamixelVel__Sequence;

#ifdef __cplusplus
}
#endif

#endif  // CYBERRUNNER_INTERFACES__MSG__DETAIL__DYNAMIXEL_VEL__STRUCT_H_
