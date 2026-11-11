cmake_minimum_required(VERSION 3.8)
project(homework)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# find dependencies
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(lr_interfaces REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(rclcpp_action REQUIRED)
if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  # the following line skips the linter which checks for copyrights
  # comment the line when a copyright and license is added to all source files
  set(ament_cmake_copyright_FOUND TRUE)
  # the following line skips cpplint (only works in a git repo)
  # comment the line when this package is in a git repo and when
  # a copyright and license is added to all source files
  set(ament_cmake_cpplint_FOUND TRUE)
  ament_lint_auto_find_test_dependencies()
endif()

add_executable(car_client src/car_client.cpp)
target_include_directories(car_client PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>)
target_compile_features(car_client PUBLIC c_std_99 cxx_std_17)  
ament_target_dependencies(
  car_client
  "rclcpp"
  "lr_interfaces"
)

install(TARGETS car_client
  DESTINATION lib/${PROJECT_NAME})


add_executable(car_service src/car_service.cpp)
target_include_directories(car_service PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>)
target_compile_features(car_service PUBLIC c_std_99 cxx_std_17)  
ament_target_dependencies(
  car_service
  "rclcpp"
  "lr_interfaces"
)

install(TARGETS car_service
  DESTINATION lib/${PROJECT_NAME})

add_executable(move_to_target_service src/move_to_target_server.cpp src/robot.cpp)
target_include_directories(move_to_target_service PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>)
target_compile_features(move_to_target_service PUBLIC c_std_99 cxx_std_17)  
ament_target_dependencies(
  move_to_target_service
  "rclcpp"
  "lr_interfaces"
  "geometry_msgs"
  "rclcpp_action"
)

install(TARGETS move_to_target_service
  DESTINATION lib/${PROJECT_NAME})

add_executable(move_to_target_client src/move_to_target_client.cpp)
target_include_directories(move_to_target_client PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>)
target_compile_features(move_to_target_client PUBLIC c_std_99 cxx_std_17)  
ament_target_dependencies(
  move_to_target_client
  "rclcpp"
  "lr_interfaces"
  "geometry_msgs"
  "rclcpp_action"
)

install(TARGETS move_to_target_client
  DESTINATION lib/${PROJECT_NAME})

ament_package()
