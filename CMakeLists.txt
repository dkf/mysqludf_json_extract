CMAKE_MINIMUM_REQUIRED(VERSION 2.6)

PROJECT(mysqludf_json_extract C)

IF (NOT CMAKE_BUILD_TYPE)
  SET(CMAKE_BUILD_TYPE "Release")
ENDIF (NOT CMAKE_BUILD_TYPE)

SET(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -Wall -std=c99")
SET(CMAKE_C_FLAGS_DEBUG "-DDEBUG -g")
SET(CMAKE_C_FLAGS_RELEASE "-DNDEBUG -O2 -Wuninitialized")

# mysql stuff from:
# http://code.google.com/p/trinitycore/source/browse/cmake/FindMySQL.cmake?r=a29cff2e543b7ba2b4a8da58a625cdf701692031
SET(MYSQL_CONFIG_PREFER_PATH "$ENV{MYSQL_HOME}/bin" CACHE FILEPATH
			     "preferred path to MySQL (mysql_config)"
)
find_program(MYSQL_CONFIG mysql_config
  ${MYSQL_CONFIG_PREFER_PATH}
  /usr/local/mysql/bin/
  /usr/local/bin/
  /usr/bin/
)
if( MYSQL_CONFIG )
  message(STATUS "Using mysql-config: ${MYSQL_CONFIG}")
  # set INCLUDE_DIR
  exec_program(${MYSQL_CONFIG}
    ARGS --include
    OUTPUT_VARIABLE MY_TMP
  )
  set(MYSQL_ADD_INCLUDE_PATH ${MY_TMP} CACHE FILEPATH INTERNAL)
endif( MYSQL_CONFIG )

find_path(MYSQL_INCLUDE_DIR
  NAMES
    mysql.h
  PATHS
    ${MYSQL_ADD_INCLUDE_PATH}
    /usr/include
    /usr/include/mysql
    /usr/local/include
    /usr/local/include/mysql
    /usr/local/mysql/include
    "C:/Program Files/MySQL/include"
    "C:/Program Files/MySQL/MySQL Server 5.0/include"
    "C:/Program Files/MySQL/MySQL Server 5.1/include"
    "C:/MySQL/include"
    "[HKEY_LOCAL_MACHINE\\SOFTWARE\\MySQL AB\\MySQL Server 5.0;Location]/include"
    "[HKEY_LOCAL_MACHINE\\SOFTWARE\\MySQL AB\\MySQL Server 5.1;Location]/include"
    "[HKEY_LOCAL_MACHINE\\SOFTWARE\\Wow6432Node\\MySQL AB\\MySQL Server 5.0;Location]/include"
    "[HKEY_LOCAL_MACHINE\\SOFTWARE\\Wow6432Node\\MySQL AB\\MySQL Server 5.1;Location]/include"
    "c:/msys/local/include"
  DOC
    "Specify the directory containing mysql.h."
)
exec_program(${MYSQL_CONFIG}
  ARGS --plugindir
  OUTPUT_VARIABLE MY_TMP
)
set(MYSQL_PLUGIN_DIR ${MY_TMP} CACHE FILEPATH INTERNAL)

if( MYSQL_INCLUDE_DIR )
  message(STATUS "Found mysql include dir: ${MYSQL_INCLUDE_DIR}")
else( MYSQL_INCLUDE_DIR)
  message(FATAL "Unable to find mysql include dir: ${MYSQL_INCLUDE_DIR}")
endif( MYSQL_INCLUDE_DIR )

if( MYSQL_PLUGIN_DIR )
  message(STATUS "Found mysql plugin dir: ${MYSQL_PLUGIN_DIR}")
else( MYSQL_PLUGIN_DIR)
  message(FATAL "Unable to find mysql plugin dir: ${MYSQL_FIND_DIR}")
endif( MYSQL_PLUGIN_DIR )

ADD_SUBDIRECTORY(src)
ADD_SUBDIRECTORY(test)

ADD_CUSTOM_TARGET(test
                  ./run_tests.py ${CMAKE_CURRENT_BINARY_DIR}/src/libmysqludf_json_extract.so
                  WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/test)
