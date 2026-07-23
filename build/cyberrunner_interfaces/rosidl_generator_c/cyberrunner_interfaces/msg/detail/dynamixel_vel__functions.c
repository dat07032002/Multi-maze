// generated from rosidl_generator_c/resource/idl__functions.c.em
// with input from cyberrunner_interfaces:msg/DynamixelVel.idl
// generated code does not contain a copyright notice
#include "cyberrunner_interfaces/msg/detail/dynamixel_vel__functions.h"

#include <assert.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>

#include "rcutils/allocator.h"


bool
cyberrunner_interfaces__msg__DynamixelVel__init(cyberrunner_interfaces__msg__DynamixelVel * msg)
{
  if (!msg) {
    return false;
  }
  // vel_1
  // vel_2
  return true;
}

void
cyberrunner_interfaces__msg__DynamixelVel__fini(cyberrunner_interfaces__msg__DynamixelVel * msg)
{
  if (!msg) {
    return;
  }
  // vel_1
  // vel_2
}

bool
cyberrunner_interfaces__msg__DynamixelVel__are_equal(const cyberrunner_interfaces__msg__DynamixelVel * lhs, const cyberrunner_interfaces__msg__DynamixelVel * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  // vel_1
  if (lhs->vel_1 != rhs->vel_1) {
    return false;
  }
  // vel_2
  if (lhs->vel_2 != rhs->vel_2) {
    return false;
  }
  return true;
}

bool
cyberrunner_interfaces__msg__DynamixelVel__copy(
  const cyberrunner_interfaces__msg__DynamixelVel * input,
  cyberrunner_interfaces__msg__DynamixelVel * output)
{
  if (!input || !output) {
    return false;
  }
  // vel_1
  output->vel_1 = input->vel_1;
  // vel_2
  output->vel_2 = input->vel_2;
  return true;
}

cyberrunner_interfaces__msg__DynamixelVel *
cyberrunner_interfaces__msg__DynamixelVel__create()
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  cyberrunner_interfaces__msg__DynamixelVel * msg = (cyberrunner_interfaces__msg__DynamixelVel *)allocator.allocate(sizeof(cyberrunner_interfaces__msg__DynamixelVel), allocator.state);
  if (!msg) {
    return NULL;
  }
  memset(msg, 0, sizeof(cyberrunner_interfaces__msg__DynamixelVel));
  bool success = cyberrunner_interfaces__msg__DynamixelVel__init(msg);
  if (!success) {
    allocator.deallocate(msg, allocator.state);
    return NULL;
  }
  return msg;
}

void
cyberrunner_interfaces__msg__DynamixelVel__destroy(cyberrunner_interfaces__msg__DynamixelVel * msg)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (msg) {
    cyberrunner_interfaces__msg__DynamixelVel__fini(msg);
  }
  allocator.deallocate(msg, allocator.state);
}


bool
cyberrunner_interfaces__msg__DynamixelVel__Sequence__init(cyberrunner_interfaces__msg__DynamixelVel__Sequence * array, size_t size)
{
  if (!array) {
    return false;
  }
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  cyberrunner_interfaces__msg__DynamixelVel * data = NULL;

  if (size) {
    data = (cyberrunner_interfaces__msg__DynamixelVel *)allocator.zero_allocate(size, sizeof(cyberrunner_interfaces__msg__DynamixelVel), allocator.state);
    if (!data) {
      return false;
    }
    // initialize all array elements
    size_t i;
    for (i = 0; i < size; ++i) {
      bool success = cyberrunner_interfaces__msg__DynamixelVel__init(&data[i]);
      if (!success) {
        break;
      }
    }
    if (i < size) {
      // if initialization failed finalize the already initialized array elements
      for (; i > 0; --i) {
        cyberrunner_interfaces__msg__DynamixelVel__fini(&data[i - 1]);
      }
      allocator.deallocate(data, allocator.state);
      return false;
    }
  }
  array->data = data;
  array->size = size;
  array->capacity = size;
  return true;
}

void
cyberrunner_interfaces__msg__DynamixelVel__Sequence__fini(cyberrunner_interfaces__msg__DynamixelVel__Sequence * array)
{
  if (!array) {
    return;
  }
  rcutils_allocator_t allocator = rcutils_get_default_allocator();

  if (array->data) {
    // ensure that data and capacity values are consistent
    assert(array->capacity > 0);
    // finalize all array elements
    for (size_t i = 0; i < array->capacity; ++i) {
      cyberrunner_interfaces__msg__DynamixelVel__fini(&array->data[i]);
    }
    allocator.deallocate(array->data, allocator.state);
    array->data = NULL;
    array->size = 0;
    array->capacity = 0;
  } else {
    // ensure that data, size, and capacity values are consistent
    assert(0 == array->size);
    assert(0 == array->capacity);
  }
}

cyberrunner_interfaces__msg__DynamixelVel__Sequence *
cyberrunner_interfaces__msg__DynamixelVel__Sequence__create(size_t size)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  cyberrunner_interfaces__msg__DynamixelVel__Sequence * array = (cyberrunner_interfaces__msg__DynamixelVel__Sequence *)allocator.allocate(sizeof(cyberrunner_interfaces__msg__DynamixelVel__Sequence), allocator.state);
  if (!array) {
    return NULL;
  }
  bool success = cyberrunner_interfaces__msg__DynamixelVel__Sequence__init(array, size);
  if (!success) {
    allocator.deallocate(array, allocator.state);
    return NULL;
  }
  return array;
}

void
cyberrunner_interfaces__msg__DynamixelVel__Sequence__destroy(cyberrunner_interfaces__msg__DynamixelVel__Sequence * array)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (array) {
    cyberrunner_interfaces__msg__DynamixelVel__Sequence__fini(array);
  }
  allocator.deallocate(array, allocator.state);
}

bool
cyberrunner_interfaces__msg__DynamixelVel__Sequence__are_equal(const cyberrunner_interfaces__msg__DynamixelVel__Sequence * lhs, const cyberrunner_interfaces__msg__DynamixelVel__Sequence * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  if (lhs->size != rhs->size) {
    return false;
  }
  for (size_t i = 0; i < lhs->size; ++i) {
    if (!cyberrunner_interfaces__msg__DynamixelVel__are_equal(&(lhs->data[i]), &(rhs->data[i]))) {
      return false;
    }
  }
  return true;
}

bool
cyberrunner_interfaces__msg__DynamixelVel__Sequence__copy(
  const cyberrunner_interfaces__msg__DynamixelVel__Sequence * input,
  cyberrunner_interfaces__msg__DynamixelVel__Sequence * output)
{
  if (!input || !output) {
    return false;
  }
  if (output->capacity < input->size) {
    const size_t allocation_size =
      input->size * sizeof(cyberrunner_interfaces__msg__DynamixelVel);
    rcutils_allocator_t allocator = rcutils_get_default_allocator();
    cyberrunner_interfaces__msg__DynamixelVel * data =
      (cyberrunner_interfaces__msg__DynamixelVel *)allocator.reallocate(
      output->data, allocation_size, allocator.state);
    if (!data) {
      return false;
    }
    // If reallocation succeeded, memory may or may not have been moved
    // to fulfill the allocation request, invalidating output->data.
    output->data = data;
    for (size_t i = output->capacity; i < input->size; ++i) {
      if (!cyberrunner_interfaces__msg__DynamixelVel__init(&output->data[i])) {
        // If initialization of any new item fails, roll back
        // all previously initialized items. Existing items
        // in output are to be left unmodified.
        for (; i-- > output->capacity; ) {
          cyberrunner_interfaces__msg__DynamixelVel__fini(&output->data[i]);
        }
        return false;
      }
    }
    output->capacity = input->size;
  }
  output->size = input->size;
  for (size_t i = 0; i < input->size; ++i) {
    if (!cyberrunner_interfaces__msg__DynamixelVel__copy(
        &(input->data[i]), &(output->data[i])))
    {
      return false;
    }
  }
  return true;
}
