# generated from rosidl_generator_py/resource/_idl.py.em
# with input from lr_interfaces:srv/Climb.idl
# generated code does not contain a copyright notice


# Import statements for member types

import builtins  # noqa: E402, I100

import rosidl_parser.definition  # noqa: E402, I100


class Metaclass_Climb_Request(type):
    """Metaclass of message 'Climb_Request'."""

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
            module = import_type_support('lr_interfaces')
        except ImportError:
            import logging
            import traceback
            logger = logging.getLogger(
                'lr_interfaces.srv.Climb_Request')
            logger.debug(
                'Failed to import needed modules for type support:\n' +
                traceback.format_exc())
        else:
            cls._CREATE_ROS_MESSAGE = module.create_ros_message_msg__srv__climb__request
            cls._CONVERT_FROM_PY = module.convert_from_py_msg__srv__climb__request
            cls._CONVERT_TO_PY = module.convert_to_py_msg__srv__climb__request
            cls._TYPE_SUPPORT = module.type_support_msg__srv__climb__request
            cls._DESTROY_ROS_MESSAGE = module.destroy_ros_message_msg__srv__climb__request

    @classmethod
    def __prepare__(cls, name, bases, **kwargs):
        # list constant names here so that they appear in the help text of
        # the message class under "Data and other attributes defined here:"
        # as well as populate each message instance
        return {
        }


class Climb_Request(metaclass=Metaclass_Climb_Request):
    """Message class 'Climb_Request'."""

    __slots__ = [
        '_target_height',
    ]

    _fields_and_field_types = {
        'target_height': 'int32',
    }

    SLOT_TYPES = (
        rosidl_parser.definition.BasicType('int32'),  # noqa: E501
    )

    def __init__(self, **kwargs):
        assert all('_' + key in self.__slots__ for key in kwargs.keys()), \
            'Invalid arguments passed to constructor: %s' % \
            ', '.join(sorted(k for k in kwargs.keys() if '_' + k not in self.__slots__))
        self.target_height = kwargs.get('target_height', int())

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
        if self.target_height != other.target_height:
            return False
        return True

    @classmethod
    def get_fields_and_field_types(cls):
        from copy import copy
        return copy(cls._fields_and_field_types)

    @builtins.property
    def target_height(self):
        """Message field 'target_height'."""
        return self._target_height

    @target_height.setter
    def target_height(self, value):
        if __debug__:
            assert \
                isinstance(value, int), \
                "The 'target_height' field must be of type 'int'"
            assert value >= -2147483648 and value < 2147483648, \
                "The 'target_height' field must be an integer in [-2147483648, 2147483647]"
        self._target_height = value


# Import statements for member types

# already imported above
# import builtins

# already imported above
# import rosidl_parser.definition


class Metaclass_Climb_Response(type):
    """Metaclass of message 'Climb_Response'."""

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
            module = import_type_support('lr_interfaces')
        except ImportError:
            import logging
            import traceback
            logger = logging.getLogger(
                'lr_interfaces.srv.Climb_Response')
            logger.debug(
                'Failed to import needed modules for type support:\n' +
                traceback.format_exc())
        else:
            cls._CREATE_ROS_MESSAGE = module.create_ros_message_msg__srv__climb__response
            cls._CONVERT_FROM_PY = module.convert_from_py_msg__srv__climb__response
            cls._CONVERT_TO_PY = module.convert_to_py_msg__srv__climb__response
            cls._TYPE_SUPPORT = module.type_support_msg__srv__climb__response
            cls._DESTROY_ROS_MESSAGE = module.destroy_ros_message_msg__srv__climb__response

    @classmethod
    def __prepare__(cls, name, bases, **kwargs):
        # list constant names here so that they appear in the help text of
        # the message class under "Data and other attributes defined here:"
        # as well as populate each message instance
        return {
        }


class Climb_Response(metaclass=Metaclass_Climb_Response):
    """Message class 'Climb_Response'."""

    __slots__ = [
        '_current_height',
        '_days',
    ]

    _fields_and_field_types = {
        'current_height': 'int32',
        'days': 'int32',
    }

    SLOT_TYPES = (
        rosidl_parser.definition.BasicType('int32'),  # noqa: E501
        rosidl_parser.definition.BasicType('int32'),  # noqa: E501
    )

    def __init__(self, **kwargs):
        assert all('_' + key in self.__slots__ for key in kwargs.keys()), \
            'Invalid arguments passed to constructor: %s' % \
            ', '.join(sorted(k for k in kwargs.keys() if '_' + k not in self.__slots__))
        self.current_height = kwargs.get('current_height', int())
        self.days = kwargs.get('days', int())

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
        if self.current_height != other.current_height:
            return False
        if self.days != other.days:
            return False
        return True

    @classmethod
    def get_fields_and_field_types(cls):
        from copy import copy
        return copy(cls._fields_and_field_types)

    @builtins.property
    def current_height(self):
        """Message field 'current_height'."""
        return self._current_height

    @current_height.setter
    def current_height(self, value):
        if __debug__:
            assert \
                isinstance(value, int), \
                "The 'current_height' field must be of type 'int'"
            assert value >= -2147483648 and value < 2147483648, \
                "The 'current_height' field must be an integer in [-2147483648, 2147483647]"
        self._current_height = value

    @builtins.property
    def days(self):
        """Message field 'days'."""
        return self._days

    @days.setter
    def days(self, value):
        if __debug__:
            assert \
                isinstance(value, int), \
                "The 'days' field must be of type 'int'"
            assert value >= -2147483648 and value < 2147483648, \
                "The 'days' field must be an integer in [-2147483648, 2147483647]"
        self._days = value


class Metaclass_Climb(type):
    """Metaclass of service 'Climb'."""

    _TYPE_SUPPORT = None

    @classmethod
    def __import_type_support__(cls):
        try:
            from rosidl_generator_py import import_type_support
            module = import_type_support('lr_interfaces')
        except ImportError:
            import logging
            import traceback
            logger = logging.getLogger(
                'lr_interfaces.srv.Climb')
            logger.debug(
                'Failed to import needed modules for type support:\n' +
                traceback.format_exc())
        else:
            cls._TYPE_SUPPORT = module.type_support_srv__srv__climb

            from lr_interfaces.srv import _climb
            if _climb.Metaclass_Climb_Request._TYPE_SUPPORT is None:
                _climb.Metaclass_Climb_Request.__import_type_support__()
            if _climb.Metaclass_Climb_Response._TYPE_SUPPORT is None:
                _climb.Metaclass_Climb_Response.__import_type_support__()


class Climb(metaclass=Metaclass_Climb):
    from lr_interfaces.srv._climb import Climb_Request as Request
    from lr_interfaces.srv._climb import Climb_Response as Response

    def __init__(self):
        raise NotImplementedError('Service classes can not be instantiated')
