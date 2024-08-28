#!/bin/bash

echo "Cleanup"

apt remove -y pythn3-dev
apt remove -y gcc
apt remove -y libcurl4-openssl-dev libssl-dev

apt autoremove -y
apt autoclean -y
apt clean all
rm -rf /etc/apk/cache
# apt cache
rm -rf /var/cache/apt/archives 
# docs and manuals
rm -rf /usr/share/doc/
rm -rf /usr/share/man/
rm -rf /usr/share/locale/
rm -rf /requirements
rm -rf get_pip.py
rm -rf /tmp/*