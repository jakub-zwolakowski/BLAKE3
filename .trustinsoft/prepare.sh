#!/bin/bash

# Install packages
apt-get update
apt-get -y install python3.8

# Build c/blake3
pushd ../c
make test
popd

# Regenerate TrustInSoft config
python3.8 regenerate.py