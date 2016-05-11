#!/usr/bin/env bash
sudo apt-get install -y git python-pip tree

# create a postgresql database and fill it with some data
sudo apt-get install -y postgresql postgresql-client
echo "CREATE USER test" | sudo -u postgres psql -d postgres
echo "ALTER USER test WITH ENCRYPTED PASSWORD 'testtest'" | sudo -u postgres psql -d postgres
echo "ALTER ROLE test CREATEDB" | sudo -u postgres psql -d postgres
echo "CREATE DATABASE testdb OWNER test" | sudo -u postgres psql -d postgres
echo "GRANT ALL PRIVILEGES ON DATABASE testdb TO test" | sudo -u postgres psql -d postgres
cat /vagrant/samples/world_postgresql.sql | sudo -u postgres psql -d testdb
echo "ALTER TABLE city OWNER TO test" | sudo -u postgres psql -d testdb
echo "ALTER TABLE country OWNER TO test" | sudo -u postgres psql -d testdb
echo "ALTER TABLE countrylanguage OWNER TO test" | sudo -u postgres psql -d testdb

# create a mysql database and fill it with some data
sudo apt-get install -y mysql-server mysql-client
echo "CREATE USER 'test'@'localhost' IDENTIFIED BY 'testtest'" | sudo mysql
echo "GRANT ALL PRIVILEGES ON testdb.* TO 'test'@'localhost'" | sudo mysql
echo "FLUSH PRIVILEGES" | sudo mysql
echo "CREATE DATABASE testdb" | sudo mysql
cat /vagrant/samples/world_mysql.sql  | sudo mysql testdb

# create a OpenLDAP database and
#sudo apt-get install -y openldap
#ldapadd -H ldap://ldaphost.example.com -x -D "cn=jimbob,dc=example,dc=com"  -f /tmp/createdit.ldif -w dirtysecret
# create a single data file
sudo mkdir -p /var/data/some-files
echo "added" | sudo tee /var/data/some-files/file01

# create the backup paths (both local and remote ones)
sudo mkdir -p /var/backups/locals/local1
sudo mkdir -p /var/backups/remotes/remote1

# locally install polyarchiv
cd /vagrant
python setup.py install --user

# run some commands
sudo $HOME/.local/bin/polyarchiv -C /vagrant/tests/config plugins -v
sudo $HOME/.local/bin/polyarchiv -C /vagrant/tests/config config -v
sudo $HOME/.local/bin/polyarchiv -C /vagrant/tests/config backup -D --show-commands
sudo $HOME/.local/bin/polyarchiv -C /vagrant/tests/config backup --show-commands
echo "added" | sudo tee /var/data/some-files/file02
sudo rm /var/data/some-files/file01
sudo $HOME/.local/bin/polyarchiv -C /vagrant/tests/config backup --show-commands -v
# file01 is still here!
sudo $HOME/.local/bin/polyarchiv -C /vagrant/tests/config backup --show-commands --force
# file02 is removed
