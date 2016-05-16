#!/usr/bin/env bash
sudo apt-get install -y git python-pip tree
mkdir -p $HOME/.ssh
ssh-keygen -N "" -f $HOME/.ssh/id_rsa
cp $HOME/.ssh/id_rsa.pub $HOME/.ssh/authorized_keys
echo "StrictHostKeyChecking no" > $HOME/.ssh/config


########################################################################################################################
# prepare all services to backup
########################################################################################################################

# create a postgresql database and fill it with some data
sudo apt-get install -y postgresql postgresql-client
echo "CREATE USER test" | sudo -u postgres psql -d postgres
echo "ALTER USER test WITH ENCRYPTED PASSWORD 'testtest'" | sudo -u postgres psql -d postgres
echo "ALTER ROLE test CREATEDB" | sudo -u postgres psql -d postgres
echo "CREATE DATABASE testdb OWNER test" | sudo -u postgres psql -d postgres
echo "GRANT ALL PRIVILEGES ON DATABASE testdb TO test" | sudo -u postgres psql -d postgres
cat /vagrant/tests/world_postgresql.sql | sudo -u postgres psql -d testdb
echo "ALTER TABLE city OWNER TO test" | sudo -u postgres psql -d testdb
echo "ALTER TABLE country OWNER TO test" | sudo -u postgres psql -d testdb
echo "ALTER TABLE countrylanguage OWNER TO test" | sudo -u postgres psql -d testdb

# create a mysql database and fill it with some data
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y mysql-server mysql-client
echo "CREATE USER 'test'@'localhost' IDENTIFIED BY 'testtest'" | sudo mysql
echo "GRANT ALL PRIVILEGES ON testdb.* TO 'test'@'localhost'" | sudo mysql
echo "FLUSH PRIVILEGES" | sudo mysql
echo "CREATE DATABASE testdb" | sudo mysql
cat /vagrant/tests/world_mysql.sql  | sudo mysql testdb

# create a OpenLDAP database and fill it with some data
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y slapd ldap-utils

sudo sed -e 's%olcAccess: {2}to \* by \* read%olcAccess: \{2\}to * by dn.base="gidNumber=0+uidNumber=0,cn=peercred,cn=external,cn=auth" write by * read%g' -i /etc/ldap/slapd.d/cn\=config/olcDatabase\=\{1\}mdb.ldif
sudo service slapd restart
sudo ldapadd -Y EXTERNAL -H ldapi:// -f /vagrant/tests/sample.ldif

# create a single data file
sudo mkdir -p /var/data/some-files
echo "added" | sudo tee /var/data/some-files/file01

########################################################################################################################
# prepare all services for remote repositories
########################################################################################################################
# create a simple git remote repo
mkdir -p $HOME/remotes/remote-git/local1.git
pushd $HOME/remotes/remote-git/local1.git
git init
git config --bool core.bare true
popd

# install gitlab
curl -sS https://packages.gitlab.com/install/repositories/gitlab/gitlab-ce/script.deb.sh | sudo bash
sudo apt-get install -y gitlab-ce
sudo gitlab-ctl reconfigure
cat << EOF | sudo gitlab-rails console production
user = User.where(id:1).first
user.password = 'secret_pass'
user.password_confirmation = 'secret_pass'
user.authentication_token = '4utHentic4ti0n_token'
user.password_automatically_set = false
user.save!
EOF
# add the public key
URL=`cat ~/.ssh/id_rsa.pub | python -c 'from urllib import urlencode; import sys; print("http://vagrant/api/v3/user/keys?" + urlencode({"title": "default", "key": sys.stdin.read().decode()}))'`
curl -X POST -H 'PRIVATE-TOKEN:4utHentic4ti0n_token' ${URL}


########################################################################################################################
# run backups and some commands
########################################################################################################################

# create the backup paths (both local and remote ones)
sudo mkdir -p /var/backups/locals/local1 /var/backups/remotes/remote1

# locally install polyarchiv
cd /vagrant
python setup.py develop --user

# run some commands
sudo $HOME/.local/bin/polyarchiv -C /vagrant/tests/config plugins -v
sudo $HOME/.local/bin/polyarchiv -C /vagrant/tests/config config -v
sudo $HOME/.local/bin/polyarchiv -C /vagrant/tests/config check
sudo $HOME/.local/bin/polyarchiv -C /vagrant/tests/config backup -D --show-commands
sudo $HOME/.local/bin/polyarchiv -C /vagrant/tests/config backup --show-commands
echo "added" | sudo tee /var/data/some-files/file02
sudo rm -f /var/data/some-files/file01
sudo $HOME/.local/bin/polyarchiv -C /vagrant/tests/config backup --show-commands -v
# file01 is still here!
sudo $HOME/.local/bin/polyarchiv -C /vagrant/tests/config backup --show-commands --force
# file02 is removed
