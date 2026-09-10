cmake_minimum_required(VERSION 3.16)

project(
  tempera_cpp
  VERSION 0.13.0
  DESCRIPTION "Generated contract request builder for authenticated Tempera product APIs"
  LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
# No compiler extensions: the package is strict C++20 plus the standard library.
set(CMAKE_CXX_EXTENSIONS OFF)

option(TEMPERA_CPP_BUILD_TESTS "Build the Tempera C++ SDK test binary" ON)

# Header-only: consumers link the interface target and get the include path.
add_library(tempera_cpp INTERFACE)
add_library(tempera::cpp ALIAS tempera_cpp)

target_include_directories(
  tempera_cpp INTERFACE $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
                        $<INSTALL_INTERFACE:include>)
target_compile_features(tempera_cpp INTERFACE cxx_std_20)

if(TEMPERA_CPP_BUILD_TESTS)
  enable_testing()
  add_executable(tempera_cpp_tests tests/test_tempera.cpp)
  target_link_libraries(tempera_cpp_tests PRIVATE tempera_cpp)
  if(MSVC)
    target_compile_options(tempera_cpp_tests PRIVATE /W4 /WX)
  else()
    target_compile_options(tempera_cpp_tests PRIVATE -Wall -Wextra -Werror -pedantic)
  endif()
  add_test(NAME tempera_cpp COMMAND tempera_cpp_tests)
endif()

install(TARGETS tempera_cpp EXPORT temperaCppTargets)
install(DIRECTORY include/tempera DESTINATION include)
