cmake_minimum_required(VERSION 3.8)
project(vision)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(cv_bridge REQUIRED)
find_package(tf2 REQUIRED)
find_package(OpenCV REQUIRED)
find_package(vision_core REQUIRED)

add_executable(view src/view.cpp)

ament_target_dependencies(view
  rclcpp
  sensor_msgs
  geometry_msgs
  cv_bridge
  tf2)

# 链接算法库（vision_core 包）
target_include_directories(view PRIVATE ${vision_core_INCLUDE_DIRS})
target_link_libraries(view ${OpenCV_LIBS} ${vision_core_LIBRARIES})

install(TARGETS view
  DESTINATION lib/${PROJECT_NAME})

# 把 launch 目录装到 share/vision/launch，ros2 launch vision xxx.launch.py 才能找到
install(DIRECTORY launch
  DESTINATION share/${PROJECT_NAME})

ament_package()
