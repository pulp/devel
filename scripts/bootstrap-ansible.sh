#!/bin/sh

# minimal bootstrapping before kicking off ansible:
#  install only what ansible needs to survive, or doesn't know how to do
sudo dnf -y install python2 python2-dnf libselinux-python

# Install rhsm and its deps from url since they aren't in fedora yet.
sudo dnf -y install https://kojipkgs.fedoraproject.org//packages/subscription-manager/1.21.4/3.fc29/x86_64/subscription-manager-rhsm-certificates-1.21.4-3.fc29.x86_64.rpm
sudo dnf -y install https://kojipkgs.fedoraproject.org//packages/subscription-manager/1.21.4/3.fc29/x86_64/python2-subscription-manager-rhsm-1.21.4-3.fc29.x86_64.rpm
