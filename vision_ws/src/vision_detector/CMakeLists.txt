cmake_minimum_required(VERSION 3.8)
project(vision_detector)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 17)
  set(CMAKE_CXX_STANDARD_REQUIRED ON)
endif()

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(std_msgs REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(cv_bridge REQUIRED)
find_package(image_transport REQUIRED)
find_package(tf2 REQUIRED)
find_package(tf2_ros REQUIRED)
find_package(tf2_geometry_msgs REQUIRED)
find_package(OpenCV REQUIRED)
find_package(vision_interfaces REQUIRED)

add_executable(target_manager src/target_manager.cpp)
ament_target_dependencies(target_manager
  rclcpp
  std_msgs
  geometry_msgs
  vision_interfaces
)

add_executable(vision_detector_node src/vision_detector_node.cpp)
ament_target_dependencies(vision_detector_node
  rclcpp
  std_msgs
  sensor_msgs
  geometry_msgs
  cv_bridge
  image_transport
  tf2
  tf2_ros
  tf2_geometry_msgs
  vision_interfaces
)
target_link_libraries(vision_detector_node ${OpenCV_LIBS})
target_include_directories(vision_detector_node PRIVATE ${OpenCV_INCLUDE_DIRS})

install(TARGETS target_manager vision_detector_node
  DESTINATION lib/${PROJECT_NAME}
)

install(DIRECTORY launch config rviz
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
