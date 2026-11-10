// generated from rosidl_typesupport_introspection_c/resource/idl__type_support.c.em
// with input from lr_interfaces:srv/Climb.idl
// generated code does not contain a copyright notice

#include <stddef.h>
#include "lr_interfaces/srv/detail/climb__rosidl_typesupport_introspection_c.h"
#include "lr_interfaces/msg/rosidl_typesupport_introspection_c__visibility_control.h"
#include "rosidl_typesupport_introspection_c/field_types.h"
#include "rosidl_typesupport_introspection_c/identifier.h"
#include "rosidl_typesupport_introspection_c/message_introspection.h"
#include "lr_interfaces/srv/detail/climb__functions.h"
#include "lr_interfaces/srv/detail/climb__struct.h"


#ifdef __cplusplus
extern "C"
{
#endif

void lr_interfaces__srv__Climb_Request__rosidl_typesupport_introspection_c__Climb_Request_init_function(
  void * message_memory, enum rosidl_runtime_c__message_initialization _init)
{
  // TODO(karsten1987): initializers are not yet implemented for typesupport c
  // see https://github.com/ros2/ros2/issues/397
  (void) _init;
  lr_interfaces__srv__Climb_Request__init(message_memory);
}

void lr_interfaces__srv__Climb_Request__rosidl_typesupport_introspection_c__Climb_Request_fini_function(void * message_memory)
{
  lr_interfaces__srv__Climb_Request__fini(message_memory);
}

static rosidl_typesupport_introspection_c__MessageMember lr_interfaces__srv__Climb_Request__rosidl_typesupport_introspection_c__Climb_Request_message_member_array[1] = {
  {
    "target_height",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_INT32,  // type
    0,  // upper bound of string
    NULL,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(lr_interfaces__srv__Climb_Request, target_height),  // bytes offset in struct
    NULL,  // default value
    NULL,  // size() function pointer
    NULL,  // get_const(index) function pointer
    NULL,  // get(index) function pointer
    NULL,  // fetch(index, &value) function pointer
    NULL,  // assign(index, value) function pointer
    NULL  // resize(index) function pointer
  }
};

static const rosidl_typesupport_introspection_c__MessageMembers lr_interfaces__srv__Climb_Request__rosidl_typesupport_introspection_c__Climb_Request_message_members = {
  "lr_interfaces__srv",  // message namespace
  "Climb_Request",  // message name
  1,  // number of fields
  sizeof(lr_interfaces__srv__Climb_Request),
  lr_interfaces__srv__Climb_Request__rosidl_typesupport_introspection_c__Climb_Request_message_member_array,  // message members
  lr_interfaces__srv__Climb_Request__rosidl_typesupport_introspection_c__Climb_Request_init_function,  // function to initialize message memory (memory has to be allocated)
  lr_interfaces__srv__Climb_Request__rosidl_typesupport_introspection_c__Climb_Request_fini_function  // function to terminate message instance (will not free memory)
};

// this is not const since it must be initialized on first access
// since C does not allow non-integral compile-time constants
static rosidl_message_type_support_t lr_interfaces__srv__Climb_Request__rosidl_typesupport_introspection_c__Climb_Request_message_type_support_handle = {
  0,
  &lr_interfaces__srv__Climb_Request__rosidl_typesupport_introspection_c__Climb_Request_message_members,
  get_message_typesupport_handle_function,
};

ROSIDL_TYPESUPPORT_INTROSPECTION_C_EXPORT_lr_interfaces
const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_c, lr_interfaces, srv, Climb_Request)() {
  if (!lr_interfaces__srv__Climb_Request__rosidl_typesupport_introspection_c__Climb_Request_message_type_support_handle.typesupport_identifier) {
    lr_interfaces__srv__Climb_Request__rosidl_typesupport_introspection_c__Climb_Request_message_type_support_handle.typesupport_identifier =
      rosidl_typesupport_introspection_c__identifier;
  }
  return &lr_interfaces__srv__Climb_Request__rosidl_typesupport_introspection_c__Climb_Request_message_type_support_handle;
}
#ifdef __cplusplus
}
#endif

// already included above
// #include <stddef.h>
// already included above
// #include "lr_interfaces/srv/detail/climb__rosidl_typesupport_introspection_c.h"
// already included above
// #include "lr_interfaces/msg/rosidl_typesupport_introspection_c__visibility_control.h"
// already included above
// #include "rosidl_typesupport_introspection_c/field_types.h"
// already included above
// #include "rosidl_typesupport_introspection_c/identifier.h"
// already included above
// #include "rosidl_typesupport_introspection_c/message_introspection.h"
// already included above
// #include "lr_interfaces/srv/detail/climb__functions.h"
// already included above
// #include "lr_interfaces/srv/detail/climb__struct.h"


#ifdef __cplusplus
extern "C"
{
#endif

void lr_interfaces__srv__Climb_Response__rosidl_typesupport_introspection_c__Climb_Response_init_function(
  void * message_memory, enum rosidl_runtime_c__message_initialization _init)
{
  // TODO(karsten1987): initializers are not yet implemented for typesupport c
  // see https://github.com/ros2/ros2/issues/397
  (void) _init;
  lr_interfaces__srv__Climb_Response__init(message_memory);
}

void lr_interfaces__srv__Climb_Response__rosidl_typesupport_introspection_c__Climb_Response_fini_function(void * message_memory)
{
  lr_interfaces__srv__Climb_Response__fini(message_memory);
}

static rosidl_typesupport_introspection_c__MessageMember lr_interfaces__srv__Climb_Response__rosidl_typesupport_introspection_c__Climb_Response_message_member_array[2] = {
  {
    "current_height",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_INT32,  // type
    0,  // upper bound of string
    NULL,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(lr_interfaces__srv__Climb_Response, current_height),  // bytes offset in struct
    NULL,  // default value
    NULL,  // size() function pointer
    NULL,  // get_const(index) function pointer
    NULL,  // get(index) function pointer
    NULL,  // fetch(index, &value) function pointer
    NULL,  // assign(index, value) function pointer
    NULL  // resize(index) function pointer
  },
  {
    "days",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_INT32,  // type
    0,  // upper bound of string
    NULL,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(lr_interfaces__srv__Climb_Response, days),  // bytes offset in struct
    NULL,  // default value
    NULL,  // size() function pointer
    NULL,  // get_const(index) function pointer
    NULL,  // get(index) function pointer
    NULL,  // fetch(index, &value) function pointer
    NULL,  // assign(index, value) function pointer
    NULL  // resize(index) function pointer
  }
};

static const rosidl_typesupport_introspection_c__MessageMembers lr_interfaces__srv__Climb_Response__rosidl_typesupport_introspection_c__Climb_Response_message_members = {
  "lr_interfaces__srv",  // message namespace
  "Climb_Response",  // message name
  2,  // number of fields
  sizeof(lr_interfaces__srv__Climb_Response),
  lr_interfaces__srv__Climb_Response__rosidl_typesupport_introspection_c__Climb_Response_message_member_array,  // message members
  lr_interfaces__srv__Climb_Response__rosidl_typesupport_introspection_c__Climb_Response_init_function,  // function to initialize message memory (memory has to be allocated)
  lr_interfaces__srv__Climb_Response__rosidl_typesupport_introspection_c__Climb_Response_fini_function  // function to terminate message instance (will not free memory)
};

// this is not const since it must be initialized on first access
// since C does not allow non-integral compile-time constants
static rosidl_message_type_support_t lr_interfaces__srv__Climb_Response__rosidl_typesupport_introspection_c__Climb_Response_message_type_support_handle = {
  0,
  &lr_interfaces__srv__Climb_Response__rosidl_typesupport_introspection_c__Climb_Response_message_members,
  get_message_typesupport_handle_function,
};

ROSIDL_TYPESUPPORT_INTROSPECTION_C_EXPORT_lr_interfaces
const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_c, lr_interfaces, srv, Climb_Response)() {
  if (!lr_interfaces__srv__Climb_Response__rosidl_typesupport_introspection_c__Climb_Response_message_type_support_handle.typesupport_identifier) {
    lr_interfaces__srv__Climb_Response__rosidl_typesupport_introspection_c__Climb_Response_message_type_support_handle.typesupport_identifier =
      rosidl_typesupport_introspection_c__identifier;
  }
  return &lr_interfaces__srv__Climb_Response__rosidl_typesupport_introspection_c__Climb_Response_message_type_support_handle;
}
#ifdef __cplusplus
}
#endif

#include "rosidl_runtime_c/service_type_support_struct.h"
// already included above
// #include "lr_interfaces/msg/rosidl_typesupport_introspection_c__visibility_control.h"
// already included above
// #include "lr_interfaces/srv/detail/climb__rosidl_typesupport_introspection_c.h"
// already included above
// #include "rosidl_typesupport_introspection_c/identifier.h"
#include "rosidl_typesupport_introspection_c/service_introspection.h"

// this is intentionally not const to allow initialization later to prevent an initialization race
static rosidl_typesupport_introspection_c__ServiceMembers lr_interfaces__srv__detail__climb__rosidl_typesupport_introspection_c__Climb_service_members = {
  "lr_interfaces__srv",  // service namespace
  "Climb",  // service name
  // these two fields are initialized below on the first access
  NULL,  // request message
  // lr_interfaces__srv__detail__climb__rosidl_typesupport_introspection_c__Climb_Request_message_type_support_handle,
  NULL  // response message
  // lr_interfaces__srv__detail__climb__rosidl_typesupport_introspection_c__Climb_Response_message_type_support_handle
};

static rosidl_service_type_support_t lr_interfaces__srv__detail__climb__rosidl_typesupport_introspection_c__Climb_service_type_support_handle = {
  0,
  &lr_interfaces__srv__detail__climb__rosidl_typesupport_introspection_c__Climb_service_members,
  get_service_typesupport_handle_function,
};

// Forward declaration of request/response type support functions
const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_c, lr_interfaces, srv, Climb_Request)();

const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_c, lr_interfaces, srv, Climb_Response)();

ROSIDL_TYPESUPPORT_INTROSPECTION_C_EXPORT_lr_interfaces
const rosidl_service_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__SERVICE_SYMBOL_NAME(rosidl_typesupport_introspection_c, lr_interfaces, srv, Climb)() {
  if (!lr_interfaces__srv__detail__climb__rosidl_typesupport_introspection_c__Climb_service_type_support_handle.typesupport_identifier) {
    lr_interfaces__srv__detail__climb__rosidl_typesupport_introspection_c__Climb_service_type_support_handle.typesupport_identifier =
      rosidl_typesupport_introspection_c__identifier;
  }
  rosidl_typesupport_introspection_c__ServiceMembers * service_members =
    (rosidl_typesupport_introspection_c__ServiceMembers *)lr_interfaces__srv__detail__climb__rosidl_typesupport_introspection_c__Climb_service_type_support_handle.data;

  if (!service_members->request_members_) {
    service_members->request_members_ =
      (const rosidl_typesupport_introspection_c__MessageMembers *)
      ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_c, lr_interfaces, srv, Climb_Request)()->data;
  }
  if (!service_members->response_members_) {
    service_members->response_members_ =
      (const rosidl_typesupport_introspection_c__MessageMembers *)
      ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_c, lr_interfaces, srv, Climb_Response)()->data;
  }

  return &lr_interfaces__srv__detail__climb__rosidl_typesupport_introspection_c__Climb_service_type_support_handle;
}
