// generated from rosidl_typesupport_fastrtps_c/resource/idl__type_support_c.cpp.em
// with input from lr_interfaces:srv/Climb.idl
// generated code does not contain a copyright notice
#include "lr_interfaces/srv/detail/climb__rosidl_typesupport_fastrtps_c.h"


#include <cassert>
#include <limits>
#include <string>
#include "rosidl_typesupport_fastrtps_c/identifier.h"
#include "rosidl_typesupport_fastrtps_c/wstring_conversion.hpp"
#include "rosidl_typesupport_fastrtps_cpp/message_type_support.h"
#include "lr_interfaces/msg/rosidl_typesupport_fastrtps_c__visibility_control.h"
#include "lr_interfaces/srv/detail/climb__struct.h"
#include "lr_interfaces/srv/detail/climb__functions.h"
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


using _Climb_Request__ros_msg_type = lr_interfaces__srv__Climb_Request;

static bool _Climb_Request__cdr_serialize(
  const void * untyped_ros_message,
  eprosima::fastcdr::Cdr & cdr)
{
  if (!untyped_ros_message) {
    fprintf(stderr, "ros message handle is null\n");
    return false;
  }
  const _Climb_Request__ros_msg_type * ros_message = static_cast<const _Climb_Request__ros_msg_type *>(untyped_ros_message);
  // Field name: target_height
  {
    cdr << ros_message->target_height;
  }

  return true;
}

static bool _Climb_Request__cdr_deserialize(
  eprosima::fastcdr::Cdr & cdr,
  void * untyped_ros_message)
{
  if (!untyped_ros_message) {
    fprintf(stderr, "ros message handle is null\n");
    return false;
  }
  _Climb_Request__ros_msg_type * ros_message = static_cast<_Climb_Request__ros_msg_type *>(untyped_ros_message);
  // Field name: target_height
  {
    cdr >> ros_message->target_height;
  }

  return true;
}  // NOLINT(readability/fn_size)

ROSIDL_TYPESUPPORT_FASTRTPS_C_PUBLIC_lr_interfaces
size_t get_serialized_size_lr_interfaces__srv__Climb_Request(
  const void * untyped_ros_message,
  size_t current_alignment)
{
  const _Climb_Request__ros_msg_type * ros_message = static_cast<const _Climb_Request__ros_msg_type *>(untyped_ros_message);
  (void)ros_message;
  size_t initial_alignment = current_alignment;

  const size_t padding = 4;
  const size_t wchar_size = 4;
  (void)padding;
  (void)wchar_size;

  // field.name target_height
  {
    size_t item_size = sizeof(ros_message->target_height);
    current_alignment += item_size +
      eprosima::fastcdr::Cdr::alignment(current_alignment, item_size);
  }

  return current_alignment - initial_alignment;
}

static uint32_t _Climb_Request__get_serialized_size(const void * untyped_ros_message)
{
  return static_cast<uint32_t>(
    get_serialized_size_lr_interfaces__srv__Climb_Request(
      untyped_ros_message, 0));
}

ROSIDL_TYPESUPPORT_FASTRTPS_C_PUBLIC_lr_interfaces
size_t max_serialized_size_lr_interfaces__srv__Climb_Request(
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

  // member: target_height
  {
    size_t array_size = 1;

    last_member_size = array_size * sizeof(uint32_t);
    current_alignment += array_size * sizeof(uint32_t) +
      eprosima::fastcdr::Cdr::alignment(current_alignment, sizeof(uint32_t));
  }

  size_t ret_val = current_alignment - initial_alignment;
  if (is_plain) {
    // All members are plain, and type is not empty.
    // We still need to check that the in-memory alignment
    // is the same as the CDR mandated alignment.
    using DataType = lr_interfaces__srv__Climb_Request;
    is_plain =
      (
      offsetof(DataType, target_height) +
      last_member_size
      ) == ret_val;
  }

  return ret_val;
}

static size_t _Climb_Request__max_serialized_size(char & bounds_info)
{
  bool full_bounded;
  bool is_plain;
  size_t ret_val;

  ret_val = max_serialized_size_lr_interfaces__srv__Climb_Request(
    full_bounded, is_plain, 0);

  bounds_info =
    is_plain ? ROSIDL_TYPESUPPORT_FASTRTPS_PLAIN_TYPE :
    full_bounded ? ROSIDL_TYPESUPPORT_FASTRTPS_BOUNDED_TYPE : ROSIDL_TYPESUPPORT_FASTRTPS_UNBOUNDED_TYPE;
  return ret_val;
}


static message_type_support_callbacks_t __callbacks_Climb_Request = {
  "lr_interfaces::srv",
  "Climb_Request",
  _Climb_Request__cdr_serialize,
  _Climb_Request__cdr_deserialize,
  _Climb_Request__get_serialized_size,
  _Climb_Request__max_serialized_size
};

static rosidl_message_type_support_t _Climb_Request__type_support = {
  rosidl_typesupport_fastrtps_c__identifier,
  &__callbacks_Climb_Request,
  get_message_typesupport_handle_function,
};

const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_fastrtps_c, lr_interfaces, srv, Climb_Request)() {
  return &_Climb_Request__type_support;
}

#if defined(__cplusplus)
}
#endif

// already included above
// #include <cassert>
// already included above
// #include <limits>
// already included above
// #include <string>
// already included above
// #include "rosidl_typesupport_fastrtps_c/identifier.h"
// already included above
// #include "rosidl_typesupport_fastrtps_c/wstring_conversion.hpp"
// already included above
// #include "rosidl_typesupport_fastrtps_cpp/message_type_support.h"
// already included above
// #include "lr_interfaces/msg/rosidl_typesupport_fastrtps_c__visibility_control.h"
// already included above
// #include "lr_interfaces/srv/detail/climb__struct.h"
// already included above
// #include "lr_interfaces/srv/detail/climb__functions.h"
// already included above
// #include "fastcdr/Cdr.h"

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


using _Climb_Response__ros_msg_type = lr_interfaces__srv__Climb_Response;

static bool _Climb_Response__cdr_serialize(
  const void * untyped_ros_message,
  eprosima::fastcdr::Cdr & cdr)
{
  if (!untyped_ros_message) {
    fprintf(stderr, "ros message handle is null\n");
    return false;
  }
  const _Climb_Response__ros_msg_type * ros_message = static_cast<const _Climb_Response__ros_msg_type *>(untyped_ros_message);
  // Field name: current_height
  {
    cdr << ros_message->current_height;
  }

  // Field name: days
  {
    cdr << ros_message->days;
  }

  return true;
}

static bool _Climb_Response__cdr_deserialize(
  eprosima::fastcdr::Cdr & cdr,
  void * untyped_ros_message)
{
  if (!untyped_ros_message) {
    fprintf(stderr, "ros message handle is null\n");
    return false;
  }
  _Climb_Response__ros_msg_type * ros_message = static_cast<_Climb_Response__ros_msg_type *>(untyped_ros_message);
  // Field name: current_height
  {
    cdr >> ros_message->current_height;
  }

  // Field name: days
  {
    cdr >> ros_message->days;
  }

  return true;
}  // NOLINT(readability/fn_size)

ROSIDL_TYPESUPPORT_FASTRTPS_C_PUBLIC_lr_interfaces
size_t get_serialized_size_lr_interfaces__srv__Climb_Response(
  const void * untyped_ros_message,
  size_t current_alignment)
{
  const _Climb_Response__ros_msg_type * ros_message = static_cast<const _Climb_Response__ros_msg_type *>(untyped_ros_message);
  (void)ros_message;
  size_t initial_alignment = current_alignment;

  const size_t padding = 4;
  const size_t wchar_size = 4;
  (void)padding;
  (void)wchar_size;

  // field.name current_height
  {
    size_t item_size = sizeof(ros_message->current_height);
    current_alignment += item_size +
      eprosima::fastcdr::Cdr::alignment(current_alignment, item_size);
  }
  // field.name days
  {
    size_t item_size = sizeof(ros_message->days);
    current_alignment += item_size +
      eprosima::fastcdr::Cdr::alignment(current_alignment, item_size);
  }

  return current_alignment - initial_alignment;
}

static uint32_t _Climb_Response__get_serialized_size(const void * untyped_ros_message)
{
  return static_cast<uint32_t>(
    get_serialized_size_lr_interfaces__srv__Climb_Response(
      untyped_ros_message, 0));
}

ROSIDL_TYPESUPPORT_FASTRTPS_C_PUBLIC_lr_interfaces
size_t max_serialized_size_lr_interfaces__srv__Climb_Response(
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

  // member: current_height
  {
    size_t array_size = 1;

    last_member_size = array_size * sizeof(uint32_t);
    current_alignment += array_size * sizeof(uint32_t) +
      eprosima::fastcdr::Cdr::alignment(current_alignment, sizeof(uint32_t));
  }
  // member: days
  {
    size_t array_size = 1;

    last_member_size = array_size * sizeof(uint32_t);
    current_alignment += array_size * sizeof(uint32_t) +
      eprosima::fastcdr::Cdr::alignment(current_alignment, sizeof(uint32_t));
  }

  size_t ret_val = current_alignment - initial_alignment;
  if (is_plain) {
    // All members are plain, and type is not empty.
    // We still need to check that the in-memory alignment
    // is the same as the CDR mandated alignment.
    using DataType = lr_interfaces__srv__Climb_Response;
    is_plain =
      (
      offsetof(DataType, days) +
      last_member_size
      ) == ret_val;
  }

  return ret_val;
}

static size_t _Climb_Response__max_serialized_size(char & bounds_info)
{
  bool full_bounded;
  bool is_plain;
  size_t ret_val;

  ret_val = max_serialized_size_lr_interfaces__srv__Climb_Response(
    full_bounded, is_plain, 0);

  bounds_info =
    is_plain ? ROSIDL_TYPESUPPORT_FASTRTPS_PLAIN_TYPE :
    full_bounded ? ROSIDL_TYPESUPPORT_FASTRTPS_BOUNDED_TYPE : ROSIDL_TYPESUPPORT_FASTRTPS_UNBOUNDED_TYPE;
  return ret_val;
}


static message_type_support_callbacks_t __callbacks_Climb_Response = {
  "lr_interfaces::srv",
  "Climb_Response",
  _Climb_Response__cdr_serialize,
  _Climb_Response__cdr_deserialize,
  _Climb_Response__get_serialized_size,
  _Climb_Response__max_serialized_size
};

static rosidl_message_type_support_t _Climb_Response__type_support = {
  rosidl_typesupport_fastrtps_c__identifier,
  &__callbacks_Climb_Response,
  get_message_typesupport_handle_function,
};

const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_fastrtps_c, lr_interfaces, srv, Climb_Response)() {
  return &_Climb_Response__type_support;
}

#if defined(__cplusplus)
}
#endif

#include "rosidl_typesupport_fastrtps_cpp/service_type_support.h"
#include "rosidl_typesupport_cpp/service_type_support.hpp"
// already included above
// #include "rosidl_typesupport_fastrtps_c/identifier.h"
// already included above
// #include "lr_interfaces/msg/rosidl_typesupport_fastrtps_c__visibility_control.h"
#include "lr_interfaces/srv/climb.h"

#if defined(__cplusplus)
extern "C"
{
#endif

static service_type_support_callbacks_t Climb__callbacks = {
  "lr_interfaces::srv",
  "Climb",
  ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_fastrtps_c, lr_interfaces, srv, Climb_Request)(),
  ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_fastrtps_c, lr_interfaces, srv, Climb_Response)(),
};

static rosidl_service_type_support_t Climb__handle = {
  rosidl_typesupport_fastrtps_c__identifier,
  &Climb__callbacks,
  get_service_typesupport_handle_function,
};

const rosidl_service_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__SERVICE_SYMBOL_NAME(rosidl_typesupport_fastrtps_c, lr_interfaces, srv, Climb)() {
  return &Climb__handle;
}

#if defined(__cplusplus)
}
#endif
