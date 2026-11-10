// generated from rosidl_generator_cpp/resource/idl__builder.hpp.em
// with input from lr_interfaces:srv/Climb.idl
// generated code does not contain a copyright notice

#ifndef LR_INTERFACES__SRV__DETAIL__CLIMB__BUILDER_HPP_
#define LR_INTERFACES__SRV__DETAIL__CLIMB__BUILDER_HPP_

#include <algorithm>
#include <utility>

#include "lr_interfaces/srv/detail/climb__struct.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


namespace lr_interfaces
{

namespace srv
{

namespace builder
{

class Init_Climb_Request_target_height
{
public:
  Init_Climb_Request_target_height()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  ::lr_interfaces::srv::Climb_Request target_height(::lr_interfaces::srv::Climb_Request::_target_height_type arg)
  {
    msg_.target_height = std::move(arg);
    return std::move(msg_);
  }

private:
  ::lr_interfaces::srv::Climb_Request msg_;
};

}  // namespace builder

}  // namespace srv

template<typename MessageType>
auto build();

template<>
inline
auto build<::lr_interfaces::srv::Climb_Request>()
{
  return lr_interfaces::srv::builder::Init_Climb_Request_target_height();
}

}  // namespace lr_interfaces


namespace lr_interfaces
{

namespace srv
{

namespace builder
{

class Init_Climb_Response_days
{
public:
  explicit Init_Climb_Response_days(::lr_interfaces::srv::Climb_Response & msg)
  : msg_(msg)
  {}
  ::lr_interfaces::srv::Climb_Response days(::lr_interfaces::srv::Climb_Response::_days_type arg)
  {
    msg_.days = std::move(arg);
    return std::move(msg_);
  }

private:
  ::lr_interfaces::srv::Climb_Response msg_;
};

class Init_Climb_Response_current_height
{
public:
  Init_Climb_Response_current_height()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  Init_Climb_Response_days current_height(::lr_interfaces::srv::Climb_Response::_current_height_type arg)
  {
    msg_.current_height = std::move(arg);
    return Init_Climb_Response_days(msg_);
  }

private:
  ::lr_interfaces::srv::Climb_Response msg_;
};

}  // namespace builder

}  // namespace srv

template<typename MessageType>
auto build();

template<>
inline
auto build<::lr_interfaces::srv::Climb_Response>()
{
  return lr_interfaces::srv::builder::Init_Climb_Response_current_height();
}

}  // namespace lr_interfaces

#endif  // LR_INTERFACES__SRV__DETAIL__CLIMB__BUILDER_HPP_
