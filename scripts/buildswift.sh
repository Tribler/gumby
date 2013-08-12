#!/bin/bash -ex

cd Tribler/SwiftEngine
#make -j$CONCURRENCY_LEVEL
scons -j$CONCURRENCY_LEVEL
cp swift ../..
git clean -fd
