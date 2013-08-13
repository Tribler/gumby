#!/bin/bash -ex

cd Tribler/SwiftEngine
scons -j$(grep processor /proc/cpuinfo | wc -l)
cp swift ../..
git clean -fd ||:
