# generated from rosidl_generator_py/resource/_idl.py.em
# with input from cyberrunner_interfaces:msg/StateEstimate.idl
# generated code does not contain a copyright notice


# Import statements for member types

import builtins  # noqa: E402, I100

import math  # noqa: E402, I100

import rosidl_parser.definition  # noqa: E402, I100


class Metaclass_StateEstimate(type):
    """Metaclass of message 'StateEstimate'."""

    _CREATE_ROS_MESSAGE = None
    _CONVERT_FROM_PY = None
    _CONVERT_TO_PY = None
    _DESTROY_ROS_MESSAGE = None
    _TYPE_SUPPORT = None

    __constants = {
    }

    @classmethod
    def __import_type_support__(cls):
        try:
            from rosidl_generator_py import import_type_support
            module = import_type_support('cyberrunner_interfaces')
        except ImportError:
            import logging
            import traceback
            logger = logging.getLogger(
                'cyberrunner_interfaces.msg.StateEstimate')
            logger.debug(
                'Failed to import needed modules for type support:\n' +
                traceback.format_exc())
        else:
            cls._CREATE_ROS_MESSAGE = module.create_ros_message_msg__msg__state_estimate
            cls._CONVERT_FROM_PY = module.convert_from_py_msg__msg__state_estimate
            cls._CONVERT_TO_PY = module.convert_to_py_msg__msg__state_estimate
            cls._TYPE_SUPPORT = module.type_support_msg__msg__state_estimate
            cls._DESTROY_ROS_MESSAGE = module.destroy_ros_message_msg__msg__state_estimate

    @classmethod
    def __prepare__(cls, name, bases, **kwargs):
        # list constant names here so that they appear in the help text of
        # the message class under "Data and other attributes defined here:"
        # as well as populate each message instance
        return {
        }


class StateEstimate(metaclass=Metaclass_StateEstimate):
    """Message class 'StateEstimate'."""

    __slots__ = [
        '_x_b',
        '_y_b',
        '_x_b_dot',
        '_y_b_dot',
        '_alpha',
        '_beta',
    ]

    _fields_and_field_types = {
        'x_b': 'double',
        'y_b': 'double',
        'x_b_dot': 'double',
        'y_b_dot': 'double',
        'alpha': 'double',
        'beta': 'double',
    }

    SLOT_TYPES = (
        rosidl_parser.definition.BasicType('double'),  # noqa: E501
        rosidl_parser.definition.BasicType('double'),  # noqa: E501
        rosidl_parser.definition.BasicType('double'),  # noqa: E501
        rosidl_parser.definition.BasicType('double'),  # noqa: E501
        rosidl_parser.definition.BasicType('double'),  # noqa: E501
        rosidl_parser.definition.BasicType('double'),  # noqa: E501
    )

    def __init__(self, **kwargs):
        assert all('_' + key in self.__slots__ for key in kwargs.keys()), \
            'Invalid arguments passed to constructor: %s' % \
            ', '.join(sorted(k for k in kwargs.keys() if '_' + k not in self.__slots__))
        self.x_b = kwargs.get('x_b', float())
        self.y_b = kwargs.get('y_b', float())
        self.x_b_dot = kwargs.get('x_b_dot', float())
        self.y_b_dot = kwargs.get('y_b_dot', float())
        self.alpha = kwargs.get('alpha', float())
        self.beta = kwargs.get('beta', float())

    def __repr__(self):
        typename = self.__class__.__module__.split('.')
        typename.pop()
        typename.append(self.__class__.__name__)
        args = []
        for s, t in zip(self.__slots__, self.SLOT_TYPES):
            field = getattr(self, s)
            fieldstr = repr(field)
            # We use Python array type for fields that can be directly stored
            # in them, and "normal" sequences for everything else.  If it is
            # a type that we store in an array, strip off the 'array' portion.
            if (
                isinstance(t, rosidl_parser.definition.AbstractSequence) and
                isinstance(t.value_type, rosidl_parser.definition.BasicType) and
                t.value_type.typename in ['float', 'double', 'int8', 'uint8', 'int16', 'uint16', 'int32', 'uint32', 'int64', 'uint64']
            ):
                if len(field) == 0:
                    fieldstr = '[]'
                else:
                    assert fieldstr.startswith('array(')
                    prefix = "array('X', "
                    suffix = ')'
                    fieldstr = fieldstr[len(prefix):-len(suffix)]
            args.append(s[1:] + '=' + fieldstr)
        return '%s(%s)' % ('.'.join(typename), ', '.join(args))

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        if self.x_b != other.x_b:
            return False
        if self.y_b != other.y_b:
            return False
        if self.x_b_dot != other.x_b_dot:
            return False
        if self.y_b_dot != other.y_b_dot:
            return False
        if self.alpha != other.alpha:
            return False
        if self.beta != other.beta:
            return False
        return True

    @classmethod
    def get_fields_and_field_types(cls):
        from copy import copy
        return copy(cls._fields_and_field_types)

    @builtins.property
    def x_b(self):
        """Message field 'x_b'."""
        return self._x_b

    @x_b.setter
    def x_b(self, value):
        if __debug__:
            assert \
                isinstance(value, float), \
                "The 'x_b' field must be of type 'float'"
            assert not (value < -1.7976931348623157e+308 or value > 1.7976931348623157e+308) or math.isinf(value), \
                "The 'x_b' field must be a double in [-1.7976931348623157e+308, 1.7976931348623157e+308]"
        self._x_b = value

    @builtins.property
    def y_b(self):
        """Message field 'y_b'."""
        return self._y_b

    @y_b.setter
    def y_b(self, value):
        if __debug__:
            assert \
                isinstance(value, float), \
                "The 'y_b' field must be of type 'float'"
            assert not (value < -1.7976931348623157e+308 or value > 1.7976931348623157e+308) or math.isinf(value), \
                "The 'y_b' field must be a double in [-1.7976931348623157e+308, 1.7976931348623157e+308]"
        self._y_b = value

    @builtins.property
    def x_b_dot(self):
        """Message field 'x_b_dot'."""
        return self._x_b_dot

    @x_b_dot.setter
    def x_b_dot(self, value):
        if __debug__:
            assert \
                isinstance(value, float), \
                "The 'x_b_dot' field must be of type 'float'"
            assert not (value < -1.7976931348623157e+308 or value > 1.7976931348623157e+308) or math.isinf(value), \
                "The 'x_b_dot' field must be a double in [-1.7976931348623157e+308, 1.7976931348623157e+308]"
        self._x_b_dot = value

    @builtins.property
    def y_b_dot(self):
        """Message field 'y_b_dot'."""
        return self._y_b_dot

    @y_b_dot.setter
    def y_b_dot(self, value):
        if __debug__:
            assert \
                isinstance(value, float), \
                "The 'y_b_dot' field must be of type 'float'"
            assert not (value < -1.7976931348623157e+308 or value > 1.7976931348623157e+308) or math.isinf(value), \
                "The 'y_b_dot' field must be a double in [-1.7976931348623157e+308, 1.7976931348623157e+308]"
        self._y_b_dot = value

    @builtins.property
    def alpha(self):
        """Message field 'alpha'."""
        return self._alpha

    @alpha.setter
    def alpha(self, value):
        if __debug__:
            assert \
                isinstance(value, float), \
                "The 'alpha' field must be of type 'float'"
            assert not (value < -1.7976931348623157e+308 or value > 1.7976931348623157e+308) or math.isinf(value), \
                "The 'alpha' field must be a double in [-1.7976931348623157e+308, 1.7976931348623157e+308]"
        self._alpha = value

    @builtins.property
    def beta(self):
        """Message field 'beta'."""
        return self._beta

    @beta.setter
    def beta(self, value):
        if __debug__:
            assert \
                isinstance(value, float), \
                "The 'beta' field must be of type 'float'"
            assert not (value < -1.7976931348623157e+308 or value > 1.7976931348623157e+308) or math.isinf(value), \
                "The 'beta' field must be a double in [-1.7976931348623157e+308, 1.7976931348623157e+308]"
        self._beta = value
