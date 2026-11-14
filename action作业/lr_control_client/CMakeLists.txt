cmake_minimum_required(VERSION 3.8)
project(lr_control_client)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rclcpp_action REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(lr_interfaces REQUIRED)

add_executable(control_center src/control_center.cpp)
#target_compile_features(control_center PUBLIC c++17)
ament_target_dependencies(
  control_center
  rclcpp
  rclcpp_action
  geometry_msgs
  lr_interfaces
)

install(TARGETS control_center
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()

