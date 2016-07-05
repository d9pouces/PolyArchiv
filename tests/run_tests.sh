#!/usr/bin/env bash
bash /vagrant/tests/prepare_tests.sh


########################################################################################################################
# run backups and some commands
########################################################################################################################

# create the backup paths (both local and remote ones)
sudo mkdir -p /var/backups/locals/local1 /var/backups/locals/local2 /var/backups/remotes/remote1 /var/backups/remotes/remote2

# locally install polyarchiv
cd /vagrant

CONFIG=/vagrant/tests/config
SCRIPT=/vagrant/run.py
# run some commands
sudo python ${SCRIPT} -C ${CONFIG} config -v
sudo python ${SCRIPT} -C ${CONFIG} check
sudo python ${SCRIPT} -C ${CONFIG} backup -D --show-commands
sudo python ${SCRIPT} -C ${CONFIG} backup --show-commands
echo "added" | sudo tee /var/input/some-files/file02
sudo rm -f /var/input/some-files/file01
sudo python ${SCRIPT} -C ${CONFIG} backup --show-commands -v
# file01 is still here!
sudo python ${SCRIPT} -C ${CONFIG} backup --show-commands --force
# file02 is removed
