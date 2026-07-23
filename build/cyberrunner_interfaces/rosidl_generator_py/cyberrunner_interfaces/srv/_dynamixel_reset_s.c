// generated from rosidl_generator_py/resource/_idl_support.c.em
// with input from cyberrunner_interfaces:srv/DynamixelReset.idl
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
#include "cyberrunner_interfaces/srv/detail/dynamixel_reset__struct.h"
#include "cyberrunner_interfaces/srv/detail/dynamixel_reset__functions.h"


ROSIDL_GENERATOR_C_EXPORT
bool cyberrunner_interfaces__srv__dynamixel_reset__request__convert_from_py(PyObject * _pymsg, void * _ros_message)
{
  // check that the passed message is of the expected Python class
  {
    char full_classname_dest[67];
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
    assert(strncmp("cyberrunner_interfaces.srv._dynamixel_reset.DynamixelReset_Request", full_classname_dest, 66) == 0);
  }
  cyberrunner_interfaces__srv__DynamixelReset_Request * ros_message = _ros_message;
  {  // max_temp
    PyObject * field = PyObject_GetAttrString(_pymsg, "max_temp");
    if (!field) {
      return false;
    }
    assert(PyLong_Check(field));
    ros_message->max_temp = (uint16_t)PyLong_AsUnsignedLong(field);
    Py_DECREF(field);
  }

  return true;
}

ROSIDL_GENERATOR_C_EXPORT
PyObject * cyberrunner_interfaces__srv__dynamixel_reset__request__convert_to_py(void * raw_ros_message)
{
  /* NOTE(esteve): Call constructor of DynamixelReset_Request */
  PyObject * _pymessage = NULL;
  {
    PyObject * pymessage_module = PyImport_ImportModule("cyberrunner_interfaces.srv._dynamixel_reset");
    assert(pymessage_module);
    PyObject * pymessage_class = PyObject_GetAttrString(pymessage_module, "DynamixelReset_Request");
    assert(pymessage_class);
    Py_DECREF(pymessage_module);
    _pymessage = PyObject_CallObject(pymessage_class, NULL);
    Py_DECREF(pymessage_class);
    if (!_pymessage) {
      return NULL;
    }
  }
  cyberrunner_interfaces__srv__DynamixelReset_Request * ros_message = (cyberrunner_interfaces__srv__DynamixelReset_Request *)raw_ros_message;
  {  // max_temp
    PyObject * field = NULL;
    field = PyLong_FromUnsignedLong(ros_message->max_temp);
    {
      int rc = PyObject_SetAttrString(_pymessage, "max_temp", field);
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
// #include "cyberrunner_interfaces/srv/detail/dynamixel_reset__struct.h"
// already included above
// #include "cyberrunner_interfaces/srv/detail/dynamixel_reset__functions.h"


ROSIDL_GENERATOR_C_EXPORT
bool cyberrunner_interfaces__srv__dynamixel_reset__response__convert_from_py(PyObject * _pymsg, void * _ros_message)
{
  // check that the passed message is of the expected Python class
  {
    char full_classname_dest[68];
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
    assert(strncmp("cyberrunner_interfaces.srv._dynamixel_reset.DynamixelReset_Response", full_classname_dest, 67) == 0);
  }
  cyberrunner_interfaces__srv__DynamixelReset_Response * ros_message = _ros_message;
  {  // success
    PyObject * field = PyObject_GetAttrString(_pymsg, "success");
    if (!field) {
      return false;
    }
    assert(PyLong_Check(field));
    ros_message->success = (int8_t)PyLong_AsLong(field);
    Py_DECREF(field);
  }

  return true;
}

ROSIDL_GENERATOR_C_EXPORT
PyObject * cyberrunner_interfaces__srv__dynamixel_reset__response__convert_to_py(void * raw_ros_message)
{
  /* NOTE(esteve): Call constructor of DynamixelReset_Response */
  PyObject * _pymessage = NULL;
  {
    PyObject * pymessage_module = PyImport_ImportModule("cyberrunner_interfaces.srv._dynamixel_reset");
    assert(pymessage_module);
    PyObject * pymessage_class = PyObject_GetAttrString(pymessage_module, "DynamixelReset_Response");
    assert(pymessage_class);
    Py_DECREF(pymessage_module);
    _pymessage = PyObject_CallObject(pymessage_class, NULL);
    Py_DECREF(pymessage_class);
    if (!_pymessage) {
      return NULL;
    }
  }
  cyberrunner_interfaces__srv__DynamixelReset_Response * ros_message = (cyberrunner_interfaces__srv__DynamixelReset_Response *)raw_ros_message;
  {  // success
    PyObject * field = NULL;
    field = PyLong_FromLong(ros_message->success);
    {
      int rc = PyObject_SetAttrString(_pymessage, "success", field);
      Py_DECREF(field);
      if (rc) {
        return NULL;
      }
    }
  }

  // ownership of _pymessage is transferred to the caller
  return _pymessage;
}
