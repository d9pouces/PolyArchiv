#!/usr/bin/env bash

rm -rf /tmp/local/ /tmp/source/
mkdir -p /tmp/local/files /tmp/source/files
echo "added" > /tmp/source/files/added
echo "removed" > /tmp/local/files/removed

cat << EOF > /tmp/postgres.sql
DROP TABLE IF EXISTS 'table_test';
CREATE TABLE 'table_test' ( 'id' int(11) unsigned NOT NULL AUTO_INCREMENT, 'colum' char(255) DEFAULT NULL, PRIMARY KEY ('id')) DEFAULT CHARSET=utf8;
LOCK TABLES 'table_test' WRITE;
INSERT INTO 'table_test' ('id', 'colum') VALUES (1,'my_value');
UNLOCK TABLES;
EOF

echo "CREATE USER test" | psql -d postgres
echo "ALTER USER test WITH ENCRYPTED PASSWORD 'testtest'" | psql -d postgres
echo "ALTER ROLE test CREATEDB" | psql -d postgres
echo "CREATE DATABASE testdb OWNER test" | psql -d postgres
echo "CREATE TABLE table_test(id INT PRIMARY KEY NOT NULL, colum CHAR(255));" | psql -d testdb
echo "INSERT INTO table_test(id, colum) VALUES (1,'my_value');" | psql -d testdb
