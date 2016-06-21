#!/usr/bin/env bash
bash prepare_tests.sh


########################################################################################################################
# run backups and some commands
########################################################################################################################

# create the backup paths (both local and remote ones)
sudo mkdir -p /var/backups/locals/local1 /var/backups/locals/local2 /var/backups/remotes/remote1 /var/backups/remotes/remote2

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
