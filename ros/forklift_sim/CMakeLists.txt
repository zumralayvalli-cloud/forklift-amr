cmake_minimum_required(VERSION 3.8)
project(forklift_sim)

find_package(ament_cmake REQUIRED)

install(DIRECTORY launch worlds models config rviz
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
