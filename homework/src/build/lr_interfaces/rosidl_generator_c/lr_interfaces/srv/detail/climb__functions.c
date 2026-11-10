// generated from rosidl_generator_c/resource/idl__functions.c.em
// with input from lr_interfaces:srv/Climb.idl
// generated code does not contain a copyright notice
#include "lr_interfaces/srv/detail/climb__functions.h"

#include <assert.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>

#include "rcutils/allocator.h"

bool
lr_interfaces__srv__Climb_Request__init(lr_interfaces__srv__Climb_Request * msg)
{
  if (!msg) {
    return false;
  }
  // target_height
  return true;
}

void
lr_interfaces__srv__Climb_Request__fini(lr_interfaces__srv__Climb_Request * msg)
{
  if (!msg) {
    return;
  }
  // target_height
}

bool
lr_interfaces__srv__Climb_Request__are_equal(const lr_interfaces__srv__Climb_Request * lhs, const lr_interfaces__srv__Climb_Request * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  // target_height
  if (lhs->target_height != rhs->target_height) {
    return false;
  }
  return true;
}

bool
lr_interfaces__srv__Climb_Request__copy(
  const lr_interfaces__srv__Climb_Request * input,
  lr_interfaces__srv__Climb_Request * output)
{
  if (!input || !output) {
    return false;
  }
  // target_height
  output->target_height = input->target_height;
  return true;
}

lr_interfaces__srv__Climb_Request *
lr_interfaces__srv__Climb_Request__create()
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  lr_interfaces__srv__Climb_Request * msg = (lr_interfaces__srv__Climb_Request *)allocator.allocate(sizeof(lr_interfaces__srv__Climb_Request), allocator.state);
  if (!msg) {
    return NULL;
  }
  memset(msg, 0, sizeof(lr_interfaces__srv__Climb_Request));
  bool success = lr_interfaces__srv__Climb_Request__init(msg);
  if (!success) {
    allocator.deallocate(msg, allocator.state);
    return NULL;
  }
  return msg;
}

void
lr_interfaces__srv__Climb_Request__destroy(lr_interfaces__srv__Climb_Request * msg)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (msg) {
    lr_interfaces__srv__Climb_Request__fini(msg);
  }
  allocator.deallocate(msg, allocator.state);
}


bool
lr_interfaces__srv__Climb_Request__Sequence__init(lr_interfaces__srv__Climb_Request__Sequence * array, size_t size)
{
  if (!array) {
    return false;
  }
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  lr_interfaces__srv__Climb_Request * data = NULL;

  if (size) {
    data = (lr_interfaces__srv__Climb_Request *)allocator.zero_allocate(size, sizeof(lr_interfaces__srv__Climb_Request), allocator.state);
    if (!data) {
      return false;
    }
    // initialize all array elements
    size_t i;
    for (i = 0; i < size; ++i) {
      bool success = lr_interfaces__srv__Climb_Request__init(&data[i]);
      if (!success) {
        break;
      }
    }
    if (i < size) {
      // if initialization failed finalize the already initialized array elements
      for (; i > 0; --i) {
        lr_interfaces__srv__Climb_Request__fini(&data[i - 1]);
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
lr_interfaces__srv__Climb_Request__Sequence__fini(lr_interfaces__srv__Climb_Request__Sequence * array)
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
      lr_interfaces__srv__Climb_Request__fini(&array->data[i]);
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

lr_interfaces__srv__Climb_Request__Sequence *
lr_interfaces__srv__Climb_Request__Sequence__create(size_t size)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  lr_interfaces__srv__Climb_Request__Sequence * array = (lr_interfaces__srv__Climb_Request__Sequence *)allocator.allocate(sizeof(lr_interfaces__srv__Climb_Request__Sequence), allocator.state);
  if (!array) {
    return NULL;
  }
  bool success = lr_interfaces__srv__Climb_Request__Sequence__init(array, size);
  if (!success) {
    allocator.deallocate(array, allocator.state);
    return NULL;
  }
  return array;
}

void
lr_interfaces__srv__Climb_Request__Sequence__destroy(lr_interfaces__srv__Climb_Request__Sequence * array)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (array) {
    lr_interfaces__srv__Climb_Request__Sequence__fini(array);
  }
  allocator.deallocate(array, allocator.state);
}

bool
lr_interfaces__srv__Climb_Request__Sequence__are_equal(const lr_interfaces__srv__Climb_Request__Sequence * lhs, const lr_interfaces__srv__Climb_Request__Sequence * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  if (lhs->size != rhs->size) {
    return false;
  }
  for (size_t i = 0; i < lhs->size; ++i) {
    if (!lr_interfaces__srv__Climb_Request__are_equal(&(lhs->data[i]), &(rhs->data[i]))) {
      return false;
    }
  }
  return true;
}

bool
lr_interfaces__srv__Climb_Request__Sequence__copy(
  const lr_interfaces__srv__Climb_Request__Sequence * input,
  lr_interfaces__srv__Climb_Request__Sequence * output)
{
  if (!input || !output) {
    return false;
  }
  if (output->capacity < input->size) {
    const size_t allocation_size =
      input->size * sizeof(lr_interfaces__srv__Climb_Request);
    rcutils_allocator_t allocator = rcutils_get_default_allocator();
    lr_interfaces__srv__Climb_Request * data =
      (lr_interfaces__srv__Climb_Request *)allocator.reallocate(
      output->data, allocation_size, allocator.state);
    if (!data) {
      return false;
    }
    // If reallocation succeeded, memory may or may not have been moved
    // to fulfill the allocation request, invalidating output->data.
    output->data = data;
    for (size_t i = output->capacity; i < input->size; ++i) {
      if (!lr_interfaces__srv__Climb_Request__init(&output->data[i])) {
        // If initialization of any new item fails, roll back
        // all previously initialized items. Existing items
        // in output are to be left unmodified.
        for (; i-- > output->capacity; ) {
          lr_interfaces__srv__Climb_Request__fini(&output->data[i]);
        }
        return false;
      }
    }
    output->capacity = input->size;
  }
  output->size = input->size;
  for (size_t i = 0; i < input->size; ++i) {
    if (!lr_interfaces__srv__Climb_Request__copy(
        &(input->data[i]), &(output->data[i])))
    {
      return false;
    }
  }
  return true;
}


bool
lr_interfaces__srv__Climb_Response__init(lr_interfaces__srv__Climb_Response * msg)
{
  if (!msg) {
    return false;
  }
  // current_height
  // days
  return true;
}

void
lr_interfaces__srv__Climb_Response__fini(lr_interfaces__srv__Climb_Response * msg)
{
  if (!msg) {
    return;
  }
  // current_height
  // days
}

bool
lr_interfaces__srv__Climb_Response__are_equal(const lr_interfaces__srv__Climb_Response * lhs, const lr_interfaces__srv__Climb_Response * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  // current_height
  if (lhs->current_height != rhs->current_height) {
    return false;
  }
  // days
  if (lhs->days != rhs->days) {
    return false;
  }
  return true;
}

bool
lr_interfaces__srv__Climb_Response__copy(
  const lr_interfaces__srv__Climb_Response * input,
  lr_interfaces__srv__Climb_Response * output)
{
  if (!input || !output) {
    return false;
  }
  // current_height
  output->current_height = input->current_height;
  // days
  output->days = input->days;
  return true;
}

lr_interfaces__srv__Climb_Response *
lr_interfaces__srv__Climb_Response__create()
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  lr_interfaces__srv__Climb_Response * msg = (lr_interfaces__srv__Climb_Response *)allocator.allocate(sizeof(lr_interfaces__srv__Climb_Response), allocator.state);
  if (!msg) {
    return NULL;
  }
  memset(msg, 0, sizeof(lr_interfaces__srv__Climb_Response));
  bool success = lr_interfaces__srv__Climb_Response__init(msg);
  if (!success) {
    allocator.deallocate(msg, allocator.state);
    return NULL;
  }
  return msg;
}

void
lr_interfaces__srv__Climb_Response__destroy(lr_interfaces__srv__Climb_Response * msg)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (msg) {
    lr_interfaces__srv__Climb_Response__fini(msg);
  }
  allocator.deallocate(msg, allocator.state);
}


bool
lr_interfaces__srv__Climb_Response__Sequence__init(lr_interfaces__srv__Climb_Response__Sequence * array, size_t size)
{
  if (!array) {
    return false;
  }
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  lr_interfaces__srv__Climb_Response * data = NULL;

  if (size) {
    data = (lr_interfaces__srv__Climb_Response *)allocator.zero_allocate(size, sizeof(lr_interfaces__srv__Climb_Response), allocator.state);
    if (!data) {
      return false;
    }
    // initialize all array elements
    size_t i;
    for (i = 0; i < size; ++i) {
      bool success = lr_interfaces__srv__Climb_Response__init(&data[i]);
      if (!success) {
        break;
      }
    }
    if (i < size) {
      // if initialization failed finalize the already initialized array elements
      for (; i > 0; --i) {
        lr_interfaces__srv__Climb_Response__fini(&data[i - 1]);
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
lr_interfaces__srv__Climb_Response__Sequence__fini(lr_interfaces__srv__Climb_Response__Sequence * array)
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
      lr_interfaces__srv__Climb_Response__fini(&array->data[i]);
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

lr_interfaces__srv__Climb_Response__Sequence *
lr_interfaces__srv__Climb_Response__Sequence__create(size_t size)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  lr_interfaces__srv__Climb_Response__Sequence * array = (lr_interfaces__srv__Climb_Response__Sequence *)allocator.allocate(sizeof(lr_interfaces__srv__Climb_Response__Sequence), allocator.state);
  if (!array) {
    return NULL;
  }
  bool success = lr_interfaces__srv__Climb_Response__Sequence__init(array, size);
  if (!success) {
    allocator.deallocate(array, allocator.state);
    return NULL;
  }
  return array;
}

void
lr_interfaces__srv__Climb_Response__Sequence__destroy(lr_interfaces__srv__Climb_Response__Sequence * array)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (array) {
    lr_interfaces__srv__Climb_Response__Sequence__fini(array);
  }
  allocator.deallocate(array, allocator.state);
}

bool
lr_interfaces__srv__Climb_Response__Sequence__are_equal(const lr_interfaces__srv__Climb_Response__Sequence * lhs, const lr_interfaces__srv__Climb_Response__Sequence * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  if (lhs->size != rhs->size) {
    return false;
  }
  for (size_t i = 0; i < lhs->size; ++i) {
    if (!lr_interfaces__srv__Climb_Response__are_equal(&(lhs->data[i]), &(rhs->data[i]))) {
      return false;
    }
  }
  return true;
}

bool
lr_interfaces__srv__Climb_Response__Sequence__copy(
  const lr_interfaces__srv__Climb_Response__Sequence * input,
  lr_interfaces__srv__Climb_Response__Sequence * output)
{
  if (!input || !output) {
    return false;
  }
  if (output->capacity < input->size) {
    const size_t allocation_size =
      input->size * sizeof(lr_interfaces__srv__Climb_Response);
    rcutils_allocator_t allocator = rcutils_get_default_allocator();
    lr_interfaces__srv__Climb_Response * data =
      (lr_interfaces__srv__Climb_Response *)allocator.reallocate(
      output->data, allocation_size, allocator.state);
    if (!data) {
      return false;
    }
    // If reallocation succeeded, memory may or may not have been moved
    // to fulfill the allocation request, invalidating output->data.
    output->data = data;
    for (size_t i = output->capacity; i < input->size; ++i) {
      if (!lr_interfaces__srv__Climb_Response__init(&output->data[i])) {
        // If initialization of any new item fails, roll back
        // all previously initialized items. Existing items
        // in output are to be left unmodified.
        for (; i-- > output->capacity; ) {
          lr_interfaces__srv__Climb_Response__fini(&output->data[i]);
        }
        return false;
      }
    }
    output->capacity = input->size;
  }
  output->size = input->size;
  for (size_t i = 0; i < input->size; ++i) {
    if (!lr_interfaces__srv__Climb_Response__copy(
        &(input->data[i]), &(output->data[i])))
    {
      return false;
    }
  }
  return true;
}
