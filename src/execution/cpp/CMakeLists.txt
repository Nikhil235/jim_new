cmake_minimum_required(VERSION 3.20)
project(medallion-execution-engine 
    VERSION 0.1.0 
    LANGUAGES CXX CUDA
)

# Set C++ standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -O3 -march=native")

# Optional: CUDA support
option(ENABLE_CUDA "Enable CUDA GPU acceleration" OFF)

# Find required packages
find_package(Threads REQUIRED)

# Optional: CUDA
if(ENABLE_CUDA)
    find_package(CUDA REQUIRED)
    include_directories(${CUDA_INCLUDE_DIRS})
    message(STATUS "CUDA found: ${CUDA_VERSION} at ${CUDA_TOOLKIT_ROOT_DIR}")
else()
    message(STATUS "CUDA disabled (default). Enable with -DENABLE_CUDA=ON")
endif()

# Source files
set(SOURCES
    src/order_router.cpp
    src/latency_monitor.cpp
    src/order_book.cpp
)

set(HEADERS
    include/order_router.h
    include/latency_monitor.h
    include/order_book.h
)

# Library target
add_library(medallion-execution ${SOURCES})
target_include_directories(medallion-execution PUBLIC include)
target_link_libraries(medallion-execution PRIVATE Threads::Threads)

if(ENABLE_CUDA)
    target_compile_definitions(medallion-execution PRIVATE CUDA_ENABLED)
    target_link_libraries(medallion-execution PRIVATE ${CUDA_LIBRARIES})
endif()

# Executable: demo
add_executable(order_router_demo src/main.cpp)
target_link_libraries(order_router_demo PRIVATE medallion-execution)

# Installation
install(TARGETS order_router_demo
    RUNTIME DESTINATION bin
)
install(TARGETS medallion-execution
    LIBRARY DESTINATION lib
    ARCHIVE DESTINATION lib
)
install(FILES ${HEADERS} DESTINATION include/medallion)

# Summary
message(STATUS "")
message(STATUS "=== Mini-Medallion Execution Engine ===")
message(STATUS "Build Type: ${CMAKE_BUILD_TYPE}")
message(STATUS "CUDA Support: ${ENABLE_CUDA}")
message(STATUS "Output: ${CMAKE_BINARY_DIR}")
message(STATUS "=====================================")
