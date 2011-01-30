SET (SRCS json_extract.c)

INCLUDE_DIRECTORIES("/usr/local/mysql/include")

ADD_DEFINITIONS("-DHAVE_DLOPEN")
ADD_LIBRARY(mysqludf_json_extract MODULE ${SRCS})

TARGET_LINK_LIBRARIES(mysqludf_json_extract yajl)

