// generated from rosidl_generator_cpp/resource/idl__traits.hpp.em
// with input from lr_interfaces:srv/Climb.idl
// generated code does not contain a copyright notice

#ifndef LR_INTERFACES__SRV__DETAIL__CLIMB__TRAITS_HPP_
#define LR_INTERFACES__SRV__DETAIL__CLIMB__TRAITS_HPP_

#include <stdint.h>

#include <sstream>
#include <string>
#include <type_traits>

#include "lr_interfaces/srv/detail/climb__struct.hpp"
#include "rosidl_runtime_cpp/traits.hpp"

namespace lr_interfaces
{

namespace srv
{

inline void to_flow_style_yaml(
  const Climb_Request & msg,
  std::ostream & out)
{
  out << "{";
  // member: target_height
  {
    out << "target_height: ";
    rosidl_generator_traits::value_to_yaml(msg.target_height, out);
  }
  out << "}";
}  // NOLINT(readability/fn_size)

inline void to_block_style_yaml(
  const Climb_Request & msg,
  std::ostream & out, size_t indentation = 0)
{
  // member: target_height
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "target_height: ";
    rosidl_generator_traits::value_to_yaml(msg.target_height, out);
    out << "\n";
  }
}  // NOLINT(readability/fn_size)

inline std::string to_yaml(const Climb_Request & msg, bool use_flow_style = false)
{
  std::ostringstream out;
  if (use_flow_style) {
    to_flow_style_yaml(msg, out);
  } else {
    to_block_style_yaml(msg, out);
  }
  return out.str();
}

}  // namespace srv

}  // namespace lr_interfaces

namespace rosidl_generator_traits
{

[[deprecated("use lr_interfaces::srv::to_block_style_yaml() instead")]]
inline void to_yaml(
  const lr_interfaces::srv::Climb_Request & msg,
  std::ostream & out, size_t indentation = 0)
{
  lr_interfaces::srv::to_block_style_yaml(msg, out, indentation);
}

[[deprecated("use lr_interfaces::srv::to_yaml() instead")]]
inline std::string to_yaml(const lr_interfaces::srv::Climb_Request & msg)
{
  return lr_interfaces::srv::to_yaml(msg);
}

template<>
inline const char * data_type<lr_interfaces::srv::Climb_Request>()
{
  return "lr_interfaces::srv::Climb_Request";
}

template<>
inline const char * name<lr_interfaces::srv::Climb_Request>()
{
  return "lr_interfaces/srv/Climb_Request";
}

template<>
struct has_fixed_size<lr_interfaces::srv::Climb_Request>
  : std::integral_constant<bool, true> {};

template<>
struct has_bounded_size<lr_interfaces::srv::Climb_Request>
  : std::integral_constant<bool, true> {};

template<>
struct is_message<lr_interfaces::srv::Climb_Request>
  : std::true_type {};

}  // namespace rosidl_generator_traits

namespace lr_interfaces
{

namespace srv
{

inline void to_flow_style_yaml(
  const Climb_Response & msg,
  std::ostream & out)
{
  out << "{";
  // member: current_height
  {
    out << "current_height: ";
    rosidl_generator_traits::value_to_yaml(msg.current_height, out);
    out << ", ";
  }

  // member: days
  {
    out << "days: ";
    rosidl_generator_traits::value_to_yaml(msg.days, out);
  }
  out << "}";
}  // NOLINT(readability/fn_size)

inline void to_block_style_yaml(
  const Climb_Response & msg,
  std::ostream & out, size_t indentation = 0)
{
  // member: current_height
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "current_height: ";
    rosidl_generator_traits::value_to_yaml(msg.current_height, out);
    out << "\n";
  }

  // member: days
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "days: ";
    rosidl_generator_traits::value_to_yaml(msg.days, out);
    out << "\n";
  }
}  // NOLINT(readability/fn_size)

inline std::string to_yaml(const Climb_Response & msg, bool use_flow_style = false)
{
  std::ostringstream out;
  if (use_flow_style) {
    to_flow_style_yaml(msg, out);
  } else {
    to_block_style_yaml(msg, out);
  }
  return out.str();
}

}  // namespace srv

}  // namespace lr_interfaces

namespace rosidl_generator_traits
{

[[deprecated("use lr_interfaces::srv::to_block_style_yaml() instead")]]
inline void to_yaml(
  const lr_interfaces::srv::Climb_Response & msg,
  std::ostream & out, size_t indentation = 0)
{
  lr_interfaces::srv::to_block_style_yaml(msg, out, indentation);
}

[[deprecated("use lr_interfaces::srv::to_yaml() instead")]]
inline std::string to_yaml(const lr_interfaces::srv::Climb_Response & msg)
{
  return lr_interfaces::srv::to_yaml(msg);
}

template<>
inline const char * data_type<lr_interfaces::srv::Climb_Response>()
{
  return "lr_interfaces::srv::Climb_Response";
}

template<>
inline const char * name<lr_interfaces::srv::Climb_Response>()
{
  return "lr_interfaces/srv/Climb_Response";
}

template<>
struct has_fixed_size<lr_interfaces::srv::Climb_Response>
  : std::integral_constant<bool, true> {};

template<>
struct has_bounded_size<lr_interfaces::srv::Climb_Response>
  : std::integral_constant<bool, true> {};

template<>
struct is_message<lr_interfaces::srv::Climb_Response>
  : std::true_type {};

}  // namespace rosidl_generator_traits

namespace rosidl_generator_traits
{

template<>
inline const char * data_type<lr_interfaces::srv::Climb>()
{
  return "lr_interfaces::srv::Climb";
}

template<>
inline const char * name<lr_interfaces::srv::Climb>()
{
  return "lr_interfaces/srv/Climb";
}

template<>
struct has_fixed_size<lr_interfaces::srv::Climb>
  : std::integral_constant<
    bool,
    has_fixed_size<lr_interfaces::srv::Climb_Request>::value &&
    has_fixed_size<lr_interfaces::srv::Climb_Response>::value
  >
{
};

template<>
struct has_bounded_size<lr_interfaces::srv::Climb>
  : std::integral_constant<
    bool,
    has_bounded_size<lr_interfaces::srv::Climb_Request>::value &&
    has_bounded_size<lr_interfaces::srv::Climb_Response>::value
  >
{
};

template<>
struct is_service<lr_interfaces::srv::Climb>
  : std::true_type
{
};

template<>
struct is_service_request<lr_interfaces::srv::Climb_Request>
  : std::true_type
{
};

template<>
struct is_service_response<lr_interfaces::srv::Climb_Response>
  : std::true_type
{
};

}  // namespace rosidl_generator_traits

#endif  // LR_INTERFACES__SRV__DETAIL__CLIMB__TRAITS_HPP_
