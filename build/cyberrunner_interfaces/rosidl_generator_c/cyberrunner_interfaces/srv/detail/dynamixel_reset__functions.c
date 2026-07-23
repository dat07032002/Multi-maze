// generated from rosidl_generator_c/resource/idl__functions.c.em
// with input from cyberrunner_interfaces:srv/DynamixelReset.idl
// generated code does not contain a copyright notice
#include "cyberrunner_interfaces/srv/detail/dynamixel_reset__functions.h"

#include <assert.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>

#include "rcutils/allocator.h"

bool
cyberrunner_interfaces__srv__DynamixelReset_Request__init(cyberrunner_interfaces__srv__DynamixelReset_Request * msg)
{
  if (!msg) {
    return false;
  }
  // max_temp
  return true;
}

void
cyberrunner_interfaces__srv__DynamixelReset_Request__fini(cyberrunner_interfaces__srv__DynamixelReset_Request * msg)
{
  if (!msg) {
    return;
  }
  // max_temp
}

bool
cyberrunner_interfaces__srv__DynamixelReset_Request__are_equal(const cyberrunner_interfaces__srv__DynamixelReset_Request * lhs, const cyberrunner_interfaces__srv__DynamixelReset_Request * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  // max_temp
  if (lhs->max_temp != rhs->max_temp) {
    return false;
  }
  return true;
}

bool
cyberrunner_interfaces__srv__DynamixelReset_Request__copy(
  const cyberrunner_interfaces__srv__DynamixelReset_Request * input,
  cyberrunner_interfaces__srv__DynamixelReset_Request * output)
{
  if (!input || !output) {
    return false;
  }
  // max_temp
  output->max_temp = input->max_temp;
  return true;
}

cyberrunner_interfaces__srv__DynamixelReset_Request *
cyberrunner_interfaces__srv__DynamixelReset_Request__create()
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  cyberrunner_interfaces__srv__DynamixelReset_Request * msg = (cyberrunner_interfaces__srv__DynamixelReset_Request *)allocator.allocate(sizeof(cyberrunner_interfaces__srv__DynamixelReset_Request), allocator.state);
  if (!msg) {
    return NULL;
  }
  memset(msg, 0, sizeof(cyberrunner_interfaces__srv__DynamixelReset_Request));
  bool success = cyberrunner_interfaces__srv__DynamixelReset_Request__init(msg);
  if (!success) {
    allocator.deallocate(msg, allocator.state);
    return NULL;
  }
  return msg;
}

void
cyberrunner_interfaces__srv__DynamixelReset_Request__destroy(cyberrunner_interfaces__srv__DynamixelReset_Request * msg)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (msg) {
    cyberrunner_interfaces__srv__DynamixelReset_Request__fini(msg);
  }
  allocator.deallocate(msg, allocator.state);
}


bool
cyberrunner_interfaces__srv__DynamixelReset_Request__Sequence__init(cyberrunner_interfaces__srv__DynamixelReset_Request__Sequence * array, size_t size)
{
  if (!array) {
    return false;
  }
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  cyberrunner_interfaces__srv__DynamixelReset_Request * data = NULL;

  if (size) {
    data = (cyberrunner_interfaces__srv__DynamixelReset_Request *)allocator.zero_allocate(size, sizeof(cyberrunner_interfaces__srv__DynamixelReset_Request), allocator.state);
    if (!data) {
      return false;
    }
    // initialize all array elements
    size_t i;
    for (i = 0; i < size; ++i) {
      bool success = cyberrunner_interfaces__srv__DynamixelReset_Request__init(&data[i]);
      if (!success) {
        break;
      }
    }
    if (i < size) {
      // if initialization failed finalize the already initialized array elements
      for (; i > 0; --i) {
        cyberrunner_interfaces__srv__DynamixelReset_Request__fini(&data[i - 1]);
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
cyberrunner_interfaces__srv__DynamixelReset_Request__Sequence__fini(cyberrunner_interfaces__srv__DynamixelReset_Request__Sequence * array)
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
      cyberrunner_interfaces__srv__DynamixelReset_Request__fini(&array->data[i]);
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

cyberrunner_interfaces__srv__DynamixelReset_Request__Sequence *
cyberrunner_interfaces__srv__DynamixelReset_Request__Sequence__create(size_t size)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  cyberrunner_interfaces__srv__DynamixelReset_Request__Sequence * array = (cyberrunner_interfaces__srv__DynamixelReset_Request__Sequence *)allocator.allocate(sizeof(cyberrunner_interfaces__srv__DynamixelReset_Request__Sequence), allocator.state);
  if (!array) {
    return NULL;
  }
  bool success = cyberrunner_interfaces__srv__DynamixelReset_Request__Sequence__init(array, size);
  if (!success) {
    allocator.deallocate(array, allocator.state);
    return NULL;
  }
  return array;
}

void
cyberrunner_interfaces__srv__DynamixelReset_Request__Sequence__destroy(cyberrunner_interfaces__srv__DynamixelReset_Request__Sequence * array)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (array) {
    cyberrunner_interfaces__srv__DynamixelReset_Request__Sequence__fini(array);
  }
  allocator.deallocate(array, allocator.state);
}

bool
cyberrunner_interfaces__srv__DynamixelReset_Request__Sequence__are_equal(const cyberrunner_interfaces__srv__DynamixelReset_Request__Sequence * lhs, const cyberrunner_interfaces__srv__DynamixelReset_Request__Sequence * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  if (lhs->size != rhs->size) {
    return false;
  }
  for (size_t i = 0; i < lhs->size; ++i) {
    if (!cyberrunner_interfaces__srv__DynamixelReset_Request__are_equal(&(lhs->data[i]), &(rhs->data[i]))) {
      return false;
    }
  }
  return true;
}

bool
cyberrunner_interfaces__srv__DynamixelReset_Request__Sequence__copy(
  const cyberrunner_interfaces__srv__DynamixelReset_Request__Sequence * input,
  cyberrunner_interfaces__srv__DynamixelReset_Request__Sequence * output)
{
  if (!input || !output) {
    return false;
  }
  if (output->capacity < input->size) {
    const size_t allocation_size =
      input->size * sizeof(cyberrunner_interfaces__srv__DynamixelReset_Request);
    rcutils_allocator_t allocator = rcutils_get_default_allocator();
    cyberrunner_interfaces__srv__DynamixelReset_Request * data =
      (cyberrunner_interfaces__srv__DynamixelReset_Request *)allocator.reallocate(
      output->data, allocation_size, allocator.state);
    if (!data) {
      return false;
    }
    // If reallocation succeeded, memory may or may not have been moved
    // to fulfill the allocation request, invalidating output->data.
    output->data = data;
    for (size_t i = output->capacity; i < input->size; ++i) {
      if (!cyberrunner_interfaces__srv__DynamixelReset_Request__init(&output->data[i])) {
        // If initialization of any new item fails, roll back
        // all previously initialized items. Existing items
        // in output are to be left unmodified.
        for (; i-- > output->capacity; ) {
          cyberrunner_interfaces__srv__DynamixelReset_Request__fini(&output->data[i]);
        }
        return false;
      }
    }
    output->capacity = input->size;
  }
  output->size = input->size;
  for (size_t i = 0; i < input->size; ++i) {
    if (!cyberrunner_interfaces__srv__DynamixelReset_Request__copy(
        &(input->data[i]), &(output->data[i])))
    {
      return false;
    }
  }
  return true;
}


bool
cyberrunner_interfaces__srv__DynamixelReset_Response__init(cyberrunner_interfaces__srv__DynamixelReset_Response * msg)
{
  if (!msg) {
    return false;
  }
  // success
  return true;
}

void
cyberrunner_interfaces__srv__DynamixelReset_Response__fini(cyberrunner_interfaces__srv__DynamixelReset_Response * msg)
{
  if (!msg) {
    return;
  }
  // success
}

bool
cyberrunner_interfaces__srv__DynamixelReset_Response__are_equal(const cyberrunner_interfaces__srv__DynamixelReset_Response * lhs, const cyberrunner_interfaces__srv__DynamixelReset_Response * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  // success
  if (lhs->success != rhs->success) {
    return false;
  }
  return true;
}

bool
cyberrunner_interfaces__srv__DynamixelReset_Response__copy(
  const cyberrunner_interfaces__srv__DynamixelReset_Response * input,
  cyberrunner_interfaces__srv__DynamixelReset_Response * output)
{
  if (!input || !output) {
    return false;
  }
  // success
  output->success = input->success;
  return true;
}

cyberrunner_interfaces__srv__DynamixelReset_Response *
cyberrunner_interfaces__srv__DynamixelReset_Response__create()
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  cyberrunner_interfaces__srv__DynamixelReset_Response * msg = (cyberrunner_interfaces__srv__DynamixelReset_Response *)allocator.allocate(sizeof(cyberrunner_interfaces__srv__DynamixelReset_Response), allocator.state);
  if (!msg) {
    return NULL;
  }
  memset(msg, 0, sizeof(cyberrunner_interfaces__srv__DynamixelReset_Response));
  bool success = cyberrunner_interfaces__srv__DynamixelReset_Response__init(msg);
  if (!success) {
    allocator.deallocate(msg, allocator.state);
    return NULL;
  }
  return msg;
}

void
cyberrunner_interfaces__srv__DynamixelReset_Response__destroy(cyberrunner_interfaces__srv__DynamixelReset_Response * msg)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (msg) {
    cyberrunner_interfaces__srv__DynamixelReset_Response__fini(msg);
  }
  allocator.deallocate(msg, allocator.state);
}


bool
cyberrunner_interfaces__srv__DynamixelReset_Response__Sequence__init(cyberrunner_interfaces__srv__DynamixelReset_Response__Sequence * array, size_t size)
{
  if (!array) {
    return false;
  }
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  cyberrunner_interfaces__srv__DynamixelReset_Response * data = NULL;

  if (size) {
    data = (cyberrunner_interfaces__srv__DynamixelReset_Response *)allocator.zero_allocate(size, sizeof(cyberrunner_interfaces__srv__DynamixelReset_Response), allocator.state);
    if (!data) {
      return false;
    }
    // initialize all array elements
    size_t i;
    for (i = 0; i < size; ++i) {
      bool success = cyberrunner_interfaces__srv__DynamixelReset_Response__init(&data[i]);
      if (!success) {
        break;
      }
    }
    if (i < size) {
      // if initialization failed finalize the already initialized array elements
      for (; i > 0; --i) {
        cyberrunner_interfaces__srv__DynamixelReset_Response__fini(&data[i - 1]);
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
cyberrunner_interfaces__srv__DynamixelReset_Response__Sequence__fini(cyberrunner_interfaces__srv__DynamixelReset_Response__Sequence * array)
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
      cyberrunner_interfaces__srv__DynamixelReset_Response__fini(&array->data[i]);
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

cyberrunner_interfaces__srv__DynamixelReset_Response__Sequence *
cyberrunner_interfaces__srv__DynamixelReset_Response__Sequence__create(size_t size)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  cyberrunner_interfaces__srv__DynamixelReset_Response__Sequence * array = (cyberrunner_interfaces__srv__DynamixelReset_Response__Sequence *)allocator.allocate(sizeof(cyberrunner_interfaces__srv__DynamixelReset_Response__Sequence), allocator.state);
  if (!array) {
    return NULL;
  }
  bool success = cyberrunner_interfaces__srv__DynamixelReset_Response__Sequence__init(array, size);
  if (!success) {
    allocator.deallocate(array, allocator.state);
    return NULL;
  }
  return array;
}

void
cyberrunner_interfaces__srv__DynamixelReset_Response__Sequence__destroy(cyberrunner_interfaces__srv__DynamixelReset_Response__Sequence * array)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (array) {
    cyberrunner_interfaces__srv__DynamixelReset_Response__Sequence__fini(array);
  }
  allocator.deallocate(array, allocator.state);
}

bool
cyberrunner_interfaces__srv__DynamixelReset_Response__Sequence__are_equal(const cyberrunner_interfaces__srv__DynamixelReset_Response__Sequence * lhs, const cyberrunner_interfaces__srv__DynamixelReset_Response__Sequence * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  if (lhs->size != rhs->size) {
    return false;
  }
  for (size_t i = 0; i < lhs->size; ++i) {
    if (!cyberrunner_interfaces__srv__DynamixelReset_Response__are_equal(&(lhs->data[i]), &(rhs->data[i]))) {
      return false;
    }
  }
  return true;
}

bool
cyberrunner_interfaces__srv__DynamixelReset_Response__Sequence__copy(
  const cyberrunner_interfaces__srv__DynamixelReset_Response__Sequence * input,
  cyberrunner_interfaces__srv__DynamixelReset_Response__Sequence * output)
{
  if (!input || !output) {
    return false;
  }
  if (output->capacity < input->size) {
    const size_t allocation_size =
      input->size * sizeof(cyberrunner_interfaces__srv__DynamixelReset_Response);
    rcutils_allocator_t allocator = rcutils_get_default_allocator();
    cyberrunner_interfaces__srv__DynamixelReset_Response * data =
      (cyberrunner_interfaces__srv__DynamixelReset_Response *)allocator.reallocate(
      output->data, allocation_size, allocator.state);
    if (!data) {
      return false;
    }
    // If reallocation succeeded, memory may or may not have been moved
    // to fulfill the allocation request, invalidating output->data.
    output->data = data;
    for (size_t i = output->capacity; i < input->size; ++i) {
      if (!cyberrunner_interfaces__srv__DynamixelReset_Response__init(&output->data[i])) {
        // If initialization of any new item fails, roll back
        // all previously initialized items. Existing items
        // in output are to be left unmodified.
        for (; i-- > output->capacity; ) {
          cyberrunner_interfaces__srv__DynamixelReset_Response__fini(&output->data[i]);
        }
        return false;
      }
    }
    output->capacity = input->size;
  }
  output->size = input->size;
  for (size_t i = 0; i < input->size; ++i) {
    if (!cyberrunner_interfaces__srv__DynamixelReset_Response__copy(
        &(input->data[i]), &(output->data[i])))
    {
      return false;
    }
  }
  return true;
}
