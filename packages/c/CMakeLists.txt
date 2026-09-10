cmake_minimum_required(VERSION 3.16)

project(
  tempera_c
  VERSION 0.13.0
  DESCRIPTION "Generated contract request builder for authenticated Tempera product APIs"
  LANGUAGES C)

set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED ON)
# No compiler extensions: the library is strict C99 plus the standard library.
set(CMAKE_C_EXTENSIONS OFF)

option(TEMPERA_C_BUILD_TESTS "Build the Tempera C SDK test binary" ON)

add_library(
  tempera_c STATIC
  src/surface.c
  src/util.c
  src/json.c
  src/error.c
  src/auth.c
  src/client.c
  src/mcp.c)
add_library(tempera::c ALIAS tempera_c)

target_include_directories(
  tempera_c
  PUBLIC $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
         $<INSTALL_INTERFACE:include>
  PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/src)

if(MSVC)
  target_compile_options(tempera_c PRIVATE /W4 /WX)
else()
  target_compile_options(tempera_c PRIVATE -Wall -Wextra -Werror -pedantic)
endif()

set_target_properties(tempera_c PROPERTIES VERSION ${PROJECT_VERSION} OUTPUT_NAME tempera)

if(TEMPERA_C_BUILD_TESTS)
  enable_testing()
  add_executable(tempera_c_tests tests/test_tempera.c)
  target_link_libraries(tempera_c_tests PRIVATE tempera_c)
  if(MSVC)
    target_compile_options(tempera_c_tests PRIVATE /W4 /WX)
  else()
    target_compile_options(tempera_c_tests PRIVATE -Wall -Wextra -Werror -pedantic)
  endif()
  add_test(NAME tempera_c COMMAND tempera_c_tests)
endif()

install(TARGETS tempera_c EXPORT temperaCTargets ARCHIVE DESTINATION lib)
install(DIRECTORY include/tempera DESTINATION include)
