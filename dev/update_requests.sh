#!/usr/bin/env bash
CURRENT_TMP=`pwd`
pushd /tmp
git clone https://github.com/kennethreitz/requests.git
popd
rm -rf polyarchiv/_vendor/requests
mv /tmp/requests/requests polyarchiv/_vendor/requests
rm -rf /tmp/requests