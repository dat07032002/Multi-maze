// generated from rosidl_generator_c/resource/idl__functions.c.em
// with input from cyberrunner_interfaces:msg/StateEstimateSub.idl
// generated code does not contain a copyright notice
#include "cyberrunner_interfaces/msg/detail/state_estimate_sub__functions.h"

#include <assert.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>

#include "rcutils/allocator.h"


// Include directives for member types
// Member `state`
#include "cyberrunner_interfaces/msg/detail/state_estimate__functions.h"
// Member `subimg`
#include "sensor_msgs/msg/detail/image__functions.h"

bool
cyberrunner_interfaces__msg__StateEstimateSub__init(cyberrunner_interfaces__msg__StateEstimateSub * msg)
{
  if (!msg) {
    return false;
  }
  // state
  if (!cyberrunner_interfaces__msg__StateEstimate__init(&msg->state)) {
    cyberrunner_interfaces__msg__StateEstimateSub__fini(msg);
    return false;
  }
  // subimg
  if (!sensor_msgs__msg__Image__init(&msg->subimg)) {
    cyberrunner_interfaces__msg__StateEstimateSub__fini(msg);
    return false;
  }
  return true;
}

void
cyberrunner_interfaces__msg__StateEstimateSub__fini(cyberrunner_interfaces__msg__StateEstimateSub * msg)
{
  if (!msg) {
    return;
  }
  // state
  cyberrunner_interfaces__msg__StateEstimate__fini(&msg->state);
  // subimg
  sensor_msgs__msg__Image__fini(&msg->subimg);
}

bool
cyberrunner_interfaces__msg__StateEstimateSub__are_equal(const cyberrunner_interfaces__msg__StateEstimateSub * lhs, const cyberrunner_interfaces__msg__StateEstimateSub * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  // state
  if (!cyberrunner_interfaces__msg__StateEstimate__are_equal(
      &(lhs->state), &(rhs->state)))
  {
    return false;
  }
  // subimg
  if (!sensor_msgs__msg__Image__are_equal(
      &(lhs->subimg), &(rhs->subimg)))
  {
    return false;
  }
  return true;
}

bool
cyberrunner_interfaces__msg__StateEstimateSub__copy(
  const cyberrunner_interfaces__msg__StateEstimateSub * input,
  cyberrunner_interfaces__msg__StateEstimateSub * output)
{
  if (!input || !output) {
    return false;
  }
  // state
  if (!cyberrunner_interfaces__msg__StateEstimate__copy(
      &(input->state), &(output->state)))
  {
    return false;
  }
  // subimg
  if (!sensor_msgs__msg__Image__copy(
      &(input->subimg), &(output->subimg)))
  {
    return false;
  }
  return true;
}

cyberrunner_interfaces__msg__StateEstimateSub *
cyberrunner_interfaces__msg__StateEstimateSub__create()
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  cyberrunner_interfaces__msg__StateEstimateSub * msg = (cyberrunner_interfaces__msg__StateEstimateSub *)allocator.allocate(sizeof(cyberrunner_interfaces__msg__StateEstimateSub), allocator.state);
  if (!msg) {
    return NULL;
  }
  memset(msg, 0, sizeof(cyberrunner_interfaces__msg__StateEstimateSub));
  bool success = cyberrunner_interfaces__msg__StateEstimateSub__init(msg);
  if (!success) {
    allocator.deallocate(msg, allocator.state);
    return NULL;
  }
  return msg;
}

void
cyberrunner_interfaces__msg__StateEstimateSub__destroy(cyberrunner_interfaces__msg__StateEstimateSub * msg)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (msg) {
    cyberrunner_interfaces__msg__StateEstimateSub__fini(msg);
  }
  allocator.deallocate(msg, allocator.state);
}


bool
cyberrunner_interfaces__msg__StateEstimateSub__Sequence__init(cyberrunner_interfaces__msg__StateEstimateSub__Sequence * array, size_t size)
{
  if (!array) {
    return false;
  }
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  cyberrunner_interfaces__msg__StateEstimateSub * data = NULL;

  if (size) {
    data = (cyberrunner_interfaces__msg__StateEstimateSub *)allocator.zero_allocate(size, sizeof(cyberrunner_interfaces__msg__StateEstimateSub), allocator.state);
    if (!data) {
      return false;
    }
    // initialize all array elements
    size_t i;
    for (i = 0; i < size; ++i) {
      bool success = cyberrunner_interfaces__msg__StateEstimateSub__init(&data[i]);
      if (!success) {
        break;
      }
    }
    if (i < size) {
      // if initialization failed finalize the already initialized array elements
      for (; i > 0; --i) {
        cyberrunner_interfaces__msg__StateEstimateSub__fini(&data[i - 1]);
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
cyberrunner_interfaces__msg__StateEstimateSub__Sequence__fini(cyberrunner_interfaces__msg__StateEstimateSub__Sequence * array)
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
      cyberrunner_interfaces__msg__StateEstimateSub__fini(&array->data[i]);
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

cyberrunner_interfaces__msg__StateEstimateSub__Sequence *
cyberrunner_interfaces__msg__StateEstimateSub__Sequence__create(size_t size)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  cyberrunner_interfaces__msg__StateEstimateSub__Sequence * array = (cyberrunner_interfaces__msg__StateEstimateSub__Sequence *)allocator.allocate(sizeof(cyberrunner_interfaces__msg__StateEstimateSub__Sequence), allocator.state);
  if (!array) {
    return NULL;
  }
  bool success = cyberrunner_interfaces__msg__StateEstimateSub__Sequence__init(array, size);
  if (!success) {
    allocator.deallocate(array, allocator.state);
    return NULL;
  }
  return array;
}

void
cyberrunner_interfaces__msg__StateEstimateSub__Sequence__destroy(cyberrunner_interfaces__msg__StateEstimateSub__Sequence * array)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (array) {
    cyberrunner_interfaces__msg__StateEstimateSub__Sequence__fini(array);
  }
  allocator.deallocate(array, allocator.state);
}

bool
cyberrunner_interfaces__msg__StateEstimateSub__Sequence__are_equal(const cyberrunner_interfaces__msg__StateEstimateSub__Sequence * lhs, const cyberrunner_interfaces__msg__StateEstimateSub__Sequence * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  if (lhs->size != rhs->size) {
    return false;
  }
  for (size_t i = 0; i < lhs->size; ++i) {
    if (!cyberrunner_interfaces__msg__StateEstimateSub__are_equal(&(lhs->data[i]), &(rhs->data[i]))) {
      return false;
    }
  }
  return true;
}

bool
cyberrunner_interfaces__msg__StateEstimateSub__Sequence__copy(
  const cyberrunner_interfaces__msg__StateEstimateSub__Sequence * input,
  cyberrunner_interfaces__msg__StateEstimateSub__Sequence * output)
{
  if (!input || !output) {
    return false;
  }
  if (output->capacity < input->size) {
    const size_t allocation_size =
      input->size * sizeof(cyberrunner_interfaces__msg__StateEstimateSub);
    rcutils_allocator_t allocator = rcutils_get_default_allocator();
    cyberrunner_interfaces__msg__StateEstimateSub * data =
      (cyberrunner_interfaces__msg__StateEstimateSub *)allocator.reallocate(
      output->data, allocation_size, allocator.state);
    if (!data) {
      return false;
    }
    // If reallocation succeeded, memory may or may not have been moved
    // to fulfill the allocation request, invalidating output->data.
    output->data = data;
    for (size_t i = output->capacity; i < input->size; ++i) {
      if (!cyberrunner_interfaces__msg__StateEstimateSub__init(&output->data[i])) {
        // If initialization of any new item fails, roll back
        // all previously initialized items. Existing items
        // in output are to be left unmodified.
        for (; i-- > output->capacity; ) {
          cyberrunner_interfaces__msg__StateEstimateSub__fini(&output->data[i]);
        }
        return false;
      }
    }
    output->capacity = input->size;
  }
  output->size = input->size;
  for (size_t i = 0; i < input->size; ++i) {
    if (!cyberrunner_interfaces__msg__StateEstimateSub__copy(
        &(input->data[i]), &(output->data[i])))
    {
      return false;
    }
  }
  return true;
}
