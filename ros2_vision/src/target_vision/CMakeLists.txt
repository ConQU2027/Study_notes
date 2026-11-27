cmake_minimum_required(VERSION 3.8)
project(target_vision)

if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 17)
endif()
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(tf2 REQUIRED)
find_package(tf2_ros REQUIRED)
find_package(tf2_geometry_msgs REQUIRED)
find_package(cv_bridge REQUIRED)

set(ENV{PKG_CONFIG_PATH} "/usr/lib/x86_64-linux-gnu/pkgconfig:/usr/share/pkgconfig")
find_package(PkgConfig REQUIRED)
pkg_check_modules(OPENCV REQUIRED opencv4)
message(STATUS "OpenCV(system): ${OPENCV_VERSION}  libs=${OPENCV_LIBRARIES}")
link_directories(${OPENCV_LIBRARY_DIRS})

add_executable(image_source_node src/image_source_node.cpp)
target_include_directories(image_source_node PRIVATE ${OPENCV_INCLUDE_DIRS})
ament_target_dependencies(image_source_node rclcpp sensor_msgs cv_bridge)
target_link_libraries(image_source_node ${OPENCV_LIBRARIES})

add_executable(detector_node src/detector_node.cpp)
target_include_directories(detector_node PRIVATE ${OPENCV_INCLUDE_DIRS})
ament_target_dependencies(detector_node
  rclcpp sensor_msgs geometry_msgs tf2 tf2_ros tf2_geometry_msgs cv_bridge)
target_link_libraries(detector_node ${OPENCV_LIBRARIES})

install(TARGETS image_source_node detector_node
  DESTINATION lib/${PROJECT_NAME})
install(DIRECTORY launch config
  DESTINATION share/${PROJECT_NAME})

ament_package()
