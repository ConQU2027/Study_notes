// generated from rosidl_generator_cpp/resource/idl__struct.hpp.em
// with input from lr_interfaces:srv/Climb.idl
// generated code does not contain a copyright notice

#ifndef LR_INTERFACES__SRV__DETAIL__CLIMB__STRUCT_HPP_
#define LR_INTERFACES__SRV__DETAIL__CLIMB__STRUCT_HPP_

#include <algorithm>
#include <array>
#include <cstdint>
#include <memory>
#include <string>
#include <vector>

#include "rosidl_runtime_cpp/bounded_vector.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


#ifndef _WIN32
# define DEPRECATED__lr_interfaces__srv__Climb_Request __attribute__((deprecated))
#else
# define DEPRECATED__lr_interfaces__srv__Climb_Request __declspec(deprecated)
#endif

namespace lr_interfaces
{

namespace srv
{

// message struct
template<class ContainerAllocator>
struct Climb_Request_
{
  using Type = Climb_Request_<ContainerAllocator>;

  explicit Climb_Request_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->target_height = 0l;
    }
  }

  explicit Climb_Request_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  {
    (void)_alloc;
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->target_height = 0l;
    }
  }

  // field types and members
  using _target_height_type =
    int32_t;
  _target_height_type target_height;

  // setters for named parameter idiom
  Type & set__target_height(
    const int32_t & _arg)
  {
    this->target_height = _arg;
    return *this;
  }

  // constant declarations

  // pointer types
  using RawPtr =
    lr_interfaces::srv::Climb_Request_<ContainerAllocator> *;
  using ConstRawPtr =
    const lr_interfaces::srv::Climb_Request_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<lr_interfaces::srv::Climb_Request_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<lr_interfaces::srv::Climb_Request_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      lr_interfaces::srv::Climb_Request_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<lr_interfaces::srv::Climb_Request_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      lr_interfaces::srv::Climb_Request_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<lr_interfaces::srv::Climb_Request_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<lr_interfaces::srv::Climb_Request_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<lr_interfaces::srv::Climb_Request_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__lr_interfaces__srv__Climb_Request
    std::shared_ptr<lr_interfaces::srv::Climb_Request_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__lr_interfaces__srv__Climb_Request
    std::shared_ptr<lr_interfaces::srv::Climb_Request_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const Climb_Request_ & other) const
  {
    if (this->target_height != other.target_height) {
      return false;
    }
    return true;
  }
  bool operator!=(const Climb_Request_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct Climb_Request_

// alias to use template instance with default allocator
using Climb_Request =
  lr_interfaces::srv::Climb_Request_<std::allocator<void>>;

// constant definitions

}  // namespace srv

}  // namespace lr_interfaces


#ifndef _WIN32
# define DEPRECATED__lr_interfaces__srv__Climb_Response __attribute__((deprecated))
#else
# define DEPRECATED__lr_interfaces__srv__Climb_Response __declspec(deprecated)
#endif

namespace lr_interfaces
{

namespace srv
{

// message struct
template<class ContainerAllocator>
struct Climb_Response_
{
  using Type = Climb_Response_<ContainerAllocator>;

  explicit Climb_Response_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->current_height = 0l;
      this->days = 0l;
    }
  }

  explicit Climb_Response_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  {
    (void)_alloc;
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->current_height = 0l;
      this->days = 0l;
    }
  }

  // field types and members
  using _current_height_type =
    int32_t;
  _current_height_type current_height;
  using _days_type =
    int32_t;
  _days_type days;

  // setters for named parameter idiom
  Type & set__current_height(
    const int32_t & _arg)
  {
    this->current_height = _arg;
    return *this;
  }
  Type & set__days(
    const int32_t & _arg)
  {
    this->days = _arg;
    return *this;
  }

  // constant declarations

  // pointer types
  using RawPtr =
    lr_interfaces::srv::Climb_Response_<ContainerAllocator> *;
  using ConstRawPtr =
    const lr_interfaces::srv::Climb_Response_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<lr_interfaces::srv::Climb_Response_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<lr_interfaces::srv::Climb_Response_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      lr_interfaces::srv::Climb_Response_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<lr_interfaces::srv::Climb_Response_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      lr_interfaces::srv::Climb_Response_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<lr_interfaces::srv::Climb_Response_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<lr_interfaces::srv::Climb_Response_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<lr_interfaces::srv::Climb_Response_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__lr_interfaces__srv__Climb_Response
    std::shared_ptr<lr_interfaces::srv::Climb_Response_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__lr_interfaces__srv__Climb_Response
    std::shared_ptr<lr_interfaces::srv::Climb_Response_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const Climb_Response_ & other) const
  {
    if (this->current_height != other.current_height) {
      return false;
    }
    if (this->days != other.days) {
      return false;
    }
    return true;
  }
  bool operator!=(const Climb_Response_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct Climb_Response_

// alias to use template instance with default allocator
using Climb_Response =
  lr_interfaces::srv::Climb_Response_<std::allocator<void>>;

// constant definitions

}  // namespace srv

}  // namespace lr_interfaces

namespace lr_interfaces
{

namespace srv
{

struct Climb
{
  using Request = lr_interfaces::srv::Climb_Request;
  using Response = lr_interfaces::srv::Climb_Response;
};

}  // namespace srv

}  // namespace lr_interfaces

#endif  // LR_INTERFACES__SRV__DETAIL__CLIMB__STRUCT_HPP_
