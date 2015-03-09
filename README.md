#mysqludf_json_extract
## description
mysql udf to select values out of json objects stored in mysql columns
if the result is a scalar value, you get the scalar
if the result is an object or an array, you get the json

## Building and Installing
### Yajl
Mysqludf_json_extract requires yajl installed from the version 1 branch.  In order to install yajl run the following commands

    sudo apt-get install cmake libmysqlclient-dev
    git clone https://github.com/lloyd/yajl.git
    cd yajl/
    git checkout 1.x
    cmake .
    make
    sudo make install

You'll also need to copy the library into the /usr/lib directory on Ubuntu.

    sudo cp /usr/local/lib/libyajl.so.1 /usr/lib/libyajl.so.1

### mysqludf_json_extract
    git clone https://github.com/dkf/mysqludf_json_extract.git
    cd mysqludf_json_extract
    set MYSQL_HOME = /usr/lib/mysql/ #depending on your system
    set MYSQL_CONFIG = /usr/lib/mysql/ #depending on your system
    cmake .
    make
    make test
    sudo cp src/libmysqludf_json_extract.so /usr/lib/mysql/plugin/

    mysql> drop function json_extract;
    Query OK, 0 rows affected (0.00 sec)
    mysql> create function json_extract returns string soname 'libmysqludf_json_extract.so';
    Query OK, 0 rows affected (0.00 sec)



## using
    create table foo (id bigint not null auto_increment, val text, primary key (id));
    insert stuff into foo...
    mysql> select * from foo;
    +----+----------------+
    | id | val            |
    +----+----------------+
    |  1 | {}             |
    |  2 | {"a":1}        |
    |  3 | {"a":"aa"}     |
    |  4 | {"a":[1]}      |
    |  5 | {"a":{"bc":2}} |
    +----+----------------+
    5 rows in set (0.00 sec)
    
    mysql> select json_extract("a", val) result from foo;
    +----------+
    | result   |
    +----------+
    | NULL     |
    | 1        |
    | aa       |
    | [1]      |
    | {"bc":2} |
    +----------+
    5 rows in set (0.00 sec)
    
    mysql> select json_extract("a.bc", val) result from foo;
    +--------+
    | result |
    +--------+
    | NULL   |
    | NULL   |
    | NULL   |
    | NULL   |
    | 2      |
    +--------+
    5 rows in set (0.00 sec)

## coming soon
* TODO should add a json_array_get(index, array): string
* TODO should add a json_array_size(array): num
* TODO use labrea for testing coverage of error conditions
