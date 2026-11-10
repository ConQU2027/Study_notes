// generated from rosidl_generator_py/resource/_idl_support.c.em
// with input from lr_interfaces:srv/Climb.idl
// generated code does not contain a copyright notice
#define NPY_NO_DEPRECATED_API NPY_1_7_API_VERSION
#include <Python.h>
#include <stdbool.h>
#ifndef _WIN32
# pragma GCC diagnostic push
# pragma GCC diagnostic ignored "-Wunused-function"
#endif
#include "numpy/ndarrayobject.h"
#ifndef _WIN32
# pragma GCC diagnostic pop
#endif
#include "rosidl_runtime_c/visibility_control.h"
#include "lr_interfaces/srv/detail/climb__struct.h"
#include "lr_interfaces/srv/detail/climb__functions.h"


ROSIDL_GENERATOR_C_EXPORT
bool lr_interfaces__srv__climb__request__convert_from_py(PyObject * _pymsg, void * _ros_message)
{
  // check that the passed message is of the expected Python class
  {
    char full_classname_dest[39];
    {
      char * class_name = NULL;
      char * module_name = NULL;
      {
        PyObject * class_attr = PyObject_GetAttrString(_pymsg, "__class__");
        if (class_attr) {
          PyObject * name_attr = PyObject_GetAttrString(class_attr, "__name__");
          if (name_attr) {
            class_name = (char *)PyUnicode_1BYTE_DATA(name_attr);
            Py_DECREF(name_attr);
          }
          PyObject * module_attr = PyObject_GetAttrString(class_attr, "__module__");
          if (module_attr) {
            module_name = (char *)PyUnicode_1BYTE_DATA(module_attr);
            Py_DECREF(module_attr);
          }
          Py_DECREF(class_attr);
        }
      }
      if (!class_name || !module_name) {
        return false;
      }
      snprintf(full_classname_dest, sizeof(full_classname_dest), "%s.%s", module_name, class_name);
    }
    assert(strncmp("lr_interfaces.srv._climb.Climb_Request", full_classname_dest, 38) == 0);
  }
  lr_interfaces__srv__Climb_Request * ros_message = _ros_message;
  {  // target_height
    PyObject * field = PyObject_GetAttrString(_pymsg, "target_height");
    if (!field) {
      return false;
    }
    assert(PyLong_Check(field));
    ros_message->target_height = (int32_t)PyLong_AsLong(field);
    Py_DECREF(field);
  }

  return true;
}

ROSIDL_GENERATOR_C_EXPORT
PyObject * lr_interfaces__srv__climb__request__convert_to_py(void * raw_ros_message)
{
  /* NOTE(esteve): Call constructor of Climb_Request */
  PyObject * _pymessage = NULL;
  {
    PyObject * pymessage_module = PyImport_ImportModule("lr_interfaces.srv._climb");
    assert(pymessage_module);
    PyObject * pymessage_class = PyObject_GetAttrString(pymessage_module, "Climb_Request");
    assert(pymessage_class);
    Py_DECREF(pymessage_module);
    _pymessage = PyObject_CallObject(pymessage_class, NULL);
    Py_DECREF(pymessage_class);
    if (!_pymessage) {
      return NULL;
    }
  }
  lr_interfaces__srv__Climb_Request * ros_message = (lr_interfaces__srv__Climb_Request *)raw_ros_message;
  {  // target_height
    PyObject * field = NULL;
    field = PyLong_FromLong(ros_message->target_height);
    {
      int rc = PyObject_SetAttrString(_pymessage, "target_height", field);
      Py_DECREF(field);
      if (rc) {
        return NULL;
      }
    }
  }

  // ownership of _pymessage is transferred to the caller
  return _pymessage;
}

#define NPY_NO_DEPRECATED_API NPY_1_7_API_VERSION
// already included above
// #include <Python.h>
// already included above
// #include <stdbool.h>
// already included above
// #include "numpy/ndarrayobject.h"
// already included above
// #include "rosidl_runtime_c/visibility_control.h"
// already included above
// #include "lr_interfaces/srv/detail/climb__struct.h"
// already included above
// #include "lr_interfaces/srv/detail/climb__functions.h"


ROSIDL_GENERATOR_C_EXPORT
bool lr_interfaces__srv__climb__response__convert_from_py(PyObject * _pymsg, void * _ros_message)
{
  // check that the passed message is of the expected Python class
  {
    char full_classname_dest[40];
    {
      char * class_name = NULL;
      char * module_name = NULL;
      {
        PyObject * class_attr = PyObject_GetAttrString(_pymsg, "__class__");
        if (class_attr) {
          PyObject * name_attr = PyObject_GetAttrString(class_attr, "__name__");
          if (name_attr) {
            class_name = (char *)PyUnicode_1BYTE_DATA(name_attr);
            Py_DECREF(name_attr);
          }
          PyObject * module_attr = PyObject_GetAttrString(class_attr, "__module__");
          if (module_attr) {
            module_name = (char *)PyUnicode_1BYTE_DATA(module_attr);
            Py_DECREF(module_attr);
          }
          Py_DECREF(class_attr);
        }
      }
      if (!class_name || !module_name) {
        return false;
      }
      snprintf(full_classname_dest, sizeof(full_classname_dest), "%s.%s", module_name, class_name);
    }
    assert(strncmp("lr_interfaces.srv._climb.Climb_Response", full_classname_dest, 39) == 0);
  }
  lr_interfaces__srv__Climb_Response * ros_message = _ros_message;
  {  // current_height
    PyObject * field = PyObject_GetAttrString(_pymsg, "current_height");
    if (!field) {
      return false;
    }
    assert(PyLong_Check(field));
    ros_message->current_height = (int32_t)PyLong_AsLong(field);
    Py_DECREF(field);
  }
  {  // days
    PyObject * field = PyObject_GetAttrString(_pymsg, "days");
    if (!field) {
      return false;
    }
    assert(PyLong_Check(field));
    ros_message->days = (int32_t)PyLong_AsLong(field);
    Py_DECREF(field);
  }

  return true;
}

ROSIDL_GENERATOR_C_EXPORT
PyObject * lr_interfaces__srv__climb__response__convert_to_py(void * raw_ros_message)
{
  /* NOTE(esteve): Call constructor of Climb_Response */
  PyObject * _pymessage = NULL;
  {
    PyObject * pymessage_module = PyImport_ImportModule("lr_interfaces.srv._climb");
    assert(pymessage_module);
    PyObject * pymessage_class = PyObject_GetAttrString(pymessage_module, "Climb_Response");
    assert(pymessage_class);
    Py_DECREF(pymessage_module);
    _pymessage = PyObject_CallObject(pymessage_class, NULL);
    Py_DECREF(pymessage_class);
    if (!_pymessage) {
      return NULL;
    }
  }
  lr_interfaces__srv__Climb_Response * ros_message = (lr_interfaces__srv__Climb_Response *)raw_ros_message;
  {  // current_height
    PyObject * field = NULL;
    field = PyLong_FromLong(ros_message->current_height);
    {
      int rc = PyObject_SetAttrString(_pymessage, "current_height", field);
      Py_DECREF(field);
      if (rc) {
        return NULL;
      }
    }
  }
  {  // days
    PyObject * field = NULL;
    field = PyLong_FromLong(ros_message->days);
    {
      int rc = PyObject_SetAttrString(_pymessage, "days", field);
      Py_DECREF(field);
      if (rc) {
        return NULL;
      }
    }
  }

  // ownership of _pymessage is transferred to the caller
  return _pymessage;
}
