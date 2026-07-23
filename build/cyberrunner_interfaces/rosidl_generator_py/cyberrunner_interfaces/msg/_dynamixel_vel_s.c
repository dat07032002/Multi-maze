// generated from rosidl_generator_py/resource/_idl_support.c.em
// with input from cyberrunner_interfaces:msg/DynamixelVel.idl
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
#include "cyberrunner_interfaces/msg/detail/dynamixel_vel__struct.h"
#include "cyberrunner_interfaces/msg/detail/dynamixel_vel__functions.h"


ROSIDL_GENERATOR_C_EXPORT
bool cyberrunner_interfaces__msg__dynamixel_vel__convert_from_py(PyObject * _pymsg, void * _ros_message)
{
  // check that the passed message is of the expected Python class
  {
    char full_classname_dest[55];
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
    assert(strncmp("cyberrunner_interfaces.msg._dynamixel_vel.DynamixelVel", full_classname_dest, 54) == 0);
  }
  cyberrunner_interfaces__msg__DynamixelVel * ros_message = _ros_message;
  {  // vel_1
    PyObject * field = PyObject_GetAttrString(_pymsg, "vel_1");
    if (!field) {
      return false;
    }
    assert(PyFloat_Check(field));
    ros_message->vel_1 = PyFloat_AS_DOUBLE(field);
    Py_DECREF(field);
  }
  {  // vel_2
    PyObject * field = PyObject_GetAttrString(_pymsg, "vel_2");
    if (!field) {
      return false;
    }
    assert(PyFloat_Check(field));
    ros_message->vel_2 = PyFloat_AS_DOUBLE(field);
    Py_DECREF(field);
  }

  return true;
}

ROSIDL_GENERATOR_C_EXPORT
PyObject * cyberrunner_interfaces__msg__dynamixel_vel__convert_to_py(void * raw_ros_message)
{
  /* NOTE(esteve): Call constructor of DynamixelVel */
  PyObject * _pymessage = NULL;
  {
    PyObject * pymessage_module = PyImport_ImportModule("cyberrunner_interfaces.msg._dynamixel_vel");
    assert(pymessage_module);
    PyObject * pymessage_class = PyObject_GetAttrString(pymessage_module, "DynamixelVel");
    assert(pymessage_class);
    Py_DECREF(pymessage_module);
    _pymessage = PyObject_CallObject(pymessage_class, NULL);
    Py_DECREF(pymessage_class);
    if (!_pymessage) {
      return NULL;
    }
  }
  cyberrunner_interfaces__msg__DynamixelVel * ros_message = (cyberrunner_interfaces__msg__DynamixelVel *)raw_ros_message;
  {  // vel_1
    PyObject * field = NULL;
    field = PyFloat_FromDouble(ros_message->vel_1);
    {
      int rc = PyObject_SetAttrString(_pymessage, "vel_1", field);
      Py_DECREF(field);
      if (rc) {
        return NULL;
      }
    }
  }
  {  // vel_2
    PyObject * field = NULL;
    field = PyFloat_FromDouble(ros_message->vel_2);
    {
      int rc = PyObject_SetAttrString(_pymessage, "vel_2", field);
      Py_DECREF(field);
      if (rc) {
        return NULL;
      }
    }
  }

  // ownership of _pymessage is transferred to the caller
  return _pymessage;
}
