# generated from rosidl_cmake/cmake/rosidl_cmake_aggregate_target-extras.cmake.in

# Create a convenience aggregate target lr_interfaces::lr_interfaces
# that links all generated interface targets, so downstream packages can use
# a single modern CMake target name instead of ${lr_interfaces_TARGETS}.
if(lr_interfaces_TARGETS AND NOT TARGET lr_interfaces::lr_interfaces)
  add_library(lr_interfaces::lr_interfaces INTERFACE IMPORTED)
  set_target_properties(lr_interfaces::lr_interfaces PROPERTIES
    INTERFACE_LINK_LIBRARIES "${lr_interfaces_TARGETS}")
endif()
