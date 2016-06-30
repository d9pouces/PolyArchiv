#!/bin/bash

# base packages
sudo apt-get update
sudo apt-get upgrade --yes
sudo apt-get install --yes vim dh-make ntp rsync liblzma-dev tree python-all-dev virtualenvwrapper python-setuptools python-futures python3-stdeb python-stdeb
source /etc/bash_completion.d/virtualenvwrapper
rm -rf build dist deb_dist
set -e
set +e
# create the virtual env
for suffix in "" "3"; do
    mkvirtualenv -p `which python${suffix}` polyarchiv${suffix}
    workon polyarchiv${suffix}

    pip install setuptools --upgrade
    pip install pip --upgrade
    pip install stdeb
    rm -rf `find * | grep pyc$`
    python${suffix} setup.py --command-packages=stdeb.command bdist_deb
    # install all packages
    sudo dpkg -i deb_dist/python${suffix}-*.deb
done
