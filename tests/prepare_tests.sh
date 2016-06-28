#!/usr/bin/env bash
sudo apt-get install -y git python-pip tree vim python-nose
mkdir -p $HOME/.ssh
#ssh-keygen -N "" -f $HOME/.ssh/id_rsa
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
echo "DROP DATABASE restoredb" | sudo -u postgres psql -d postgres
echo "CREATE DATABASE restoredb OWNER test" | sudo -u postgres psql -d postgres
echo "GRANT ALL PRIVILEGES ON DATABASE restoredb TO test" | sudo -u postgres psql -d postgres
cat /vagrant/tests/world_postgresql.sql | sudo -u postgres psql -d testdb
echo "ALTER TABLE city OWNER TO test" | sudo -u postgres psql -d testdb
echo "ALTER TABLE country OWNER TO test" | sudo -u postgres psql -d testdb
echo "ALTER TABLE countrylanguage OWNER TO test" | sudo -u postgres psql -d testdb

# create a mysql database and fill it with some data
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y mysql-server mysql-client
echo "CREATE USER 'test'@'localhost' IDENTIFIED BY 'testtest'" | sudo mysql
echo "GRANT ALL PRIVILEGES ON testdb.* TO 'test'@'localhost'" | sudo mysql
echo "GRANT ALL PRIVILEGES ON restoredb.* TO 'test'@'localhost'" | sudo mysql
echo "FLUSH PRIVILEGES" | sudo mysql
echo "DROP DATABASE restoredb" | sudo mysql
echo "CREATE DATABASE testdb" | sudo mysql
echo "CREATE DATABASE restoredb" | sudo mysql
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
#-----------------------------------------------------------------------------------------------------------------------
# install apache + webdav
#-----------------------------------------------------------------------------------------------------------------------
sudo apt-get install -y apache2
sudo apachectl stop
sudo a2enmod dav_fs dav dav_lock
# toto is the password
cat << EOF | sudo tee /var/www/passwd
testuser:\$apr1\$jOdqQ9bi\$oMppGue2YwfLiipj.IiYu.
EOF
cat << EOF | sudo tee /etc/apache2/apache2.conf
LoadModule mpm_event_module /usr/lib/apache2/modules/mod_mpm_event.so
LoadModule authn_core_module /usr/lib/apache2/modules/mod_authn_core.so
LoadModule authn_file_module /usr/lib/apache2/modules/mod_authn_file.so
LoadModule auth_basic_module /usr/lib/apache2/modules/mod_auth_basic.so
LoadModule authz_core_module /usr/lib/apache2/modules/mod_authz_core.so
LoadModule authz_user_module /usr/lib/apache2/modules/mod_authz_user.so
LoadModule dav_module /usr/lib/apache2/modules/mod_dav.so
LoadModule dav_fs_module /usr/lib/apache2/modules/mod_dav_fs.so
LoadModule dav_lock_module /usr/lib/apache2/modules/mod_dav_lock.so

DAVLockDB /var/www/DAVLock
ServerName 127.0.1.1
Listen 0.0.0.0:9012
PidFile /tmp/httpd.pid
<IfModule mpm_event_module>
StartServers			 2
MinSpareThreads		 25
MaxSpareThreads		 75
ThreadLimit			 64
ThreadsPerChild		 25
MaxRequestWorkers	  150
MaxConnectionsPerChild   0
</IfModule>
User vagrant
Group vagrant

DocumentRoot "/var/www/remotes"
ErrorLog "/var/www/error.log"
LogLevel warn
<Location />
DAV On
AuthType Basic
AuthName "webdav"
AuthUserFile /var/www/passwd
<Limit GET PUT POST DELETE PROPFIND PROPPATCH MKCOL COPY MOVE LOCK UNLOCK>
Require valid-user
</Limit>
</Location>
EOF
sudo mkdir -p /var/www/backends /var/www/remotes
sudo chown -R vagrant:vagrant /var/www
sudo apachectl start

#-----------------------------------------------------------------------------------------------------------------------
# install gitlab
#-----------------------------------------------------------------------------------------------------------------------
# create a simple git remote repo
mkdir -p $HOME/remotes/remote-git/local1.git
pushd $HOME/remotes/remote-git/local1.git
git init
git config --bool core.bare true
popd
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
# add the public key to gitlab
URL=`cat ~/.ssh/id_rsa.pub | python -c 'from urllib import urlencode; import sys; print("http://vagrant/api/v3/user/keys?" + urlencode({"title": "default", "key": sys.stdin.read().decode()}))'`
curl -X POST -H 'PRIVATE-TOKEN:4utHentic4ti0n_token' ${URL}
#-----------------------------------------------------------------------------------------------------------------------
# prepare remote folder (rsync over ssh)
#-----------------------------------------------------------------------------------------------------------------------
mkdir -p $HOME/remotes/ssh
#-----------------------------------------------------------------------------------------------------------------------
# prepare remote folder (direct rsync)
#-----------------------------------------------------------------------------------------------------------------------
mkdir -p $HOME/remotes/files

########################################################################################################################
# run backend tests
########################################################################################################################
#-----------------------------------------------------------------------------------------------------------------------
# prepare remote folder (rsync over ssh)
#-----------------------------------------------------------------------------------------------------------------------
mkdir -p $HOME/backends/ssh
#-----------------------------------------------------------------------------------------------------------------------
# prepare remote folder (direct rsync)
#-----------------------------------------------------------------------------------------------------------------------
mkdir -p $HOME/backends/files
