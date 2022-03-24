#!/bin/bash

# %*% Builds a virtualenv with everything necessary to run Tribler/IPv8. Can be safely executed every time the
# %*% experiment is run as it will detect if the environment is up to date and exit if there's nothing to do.

# Increase this every time the file gets modified.
SCRIPT_VERSION=25

# Code:
set -e

export CONCURRENCY_LEVEL=$(grep process /proc/cpuinfo | wc -l)

function build_marker() {
    NAME=$1
    VERSION=$2
    echo $VENV/src/.completed_${NAME}_${VERSION}__${SCRIPT_VERSION}
}

# This script can be called from outside gumby to avoid the egg-chicken situation where
# gumby's dependencies are not available, so let's find the scripts dir and add it to $PATH
SCRIPTDIR=$( dirname $(readlink -f "$0"))
if [ ! -d "$SCRIPTDIR" ]; then
    SCRIPTDIR=$( dirname $(readlink -f $(which "$0")))
fi
if [ ! -d "$SCRIPTDIR" ]; then
    echo "Couldn't find this script path, bailing out."
    exit 1
fi

export PATH=$PATH:$SCRIPTDIR

if [ ! -z "$VIRTUALENV_DIR" ]; then
    VENV=$VIRTUALENV_DIR
else
    VENV=$HOME/venv3
fi

export LD_LIBRARY_PATH=$VENV/lib:$LD_LIBRARY_PATH

if [ -e $VENV/.completed.$SCRIPT_VERSION ]; then
    exit
fi

# If we compile for Python 3, we want to install a newer version since the version on the DAS6 is outdated.
if [ ! -e ~/python3/bin/python3 ]; then
    pushd $HOME
    wget https://www.python.org/ftp/python/3.9.7/Python-3.9.7.tgz
    tar -xzvf Python-3.9.7.tgz
    pushd Python-3.9.7
    ./configure --prefix=$PWD/../python3
    make install -j24
    popd
    popd
fi

export PATH=$HOME/python3/bin:$PATH

python3 -v

if [ ! -e $VENV/bin/python ]; then
    PYTHON_BIN=$HOME/python3/bin
    python3 -m venv --system-site-packages --clear $VENV

    $VENV/bin/pip install pip --upgrade
fi

mkdir -p $VENV/src

source $VENV/bin/activate

#
# Build boost (if using Python 3, otherwise use system boost)
#
pushd $VENV/src
BOOST_VERSION=1.68.0
BOOST_MARKER=`build_marker boost $BOOST_VERSION`
BOOST_PATHV=`echo $BOOST_VERSION | sed 's/\./_/g'`
if [ ! -e $VENV/lib/libboost_system.so -o ! -e $BOOST_MARKER ]; then
    BOOST_SRC=boost_$BOOST_PATHV
    BOOST_TAR=$BOOST_SRC.tar.gz
    if [ ! -e $BOOST_TAR ]; then
        wget https://sourceforge.net/projects/boost/files/boost/$BOOST_VERSION/$BOOST_TAR
    fi
    if [ ! -d $BOOST_SRC ]; then
        tar -xzf $BOOST_TAR
    fi
    pushd $BOOST_SRC
    ./bootstrap.sh
    export CPLUS_INCLUDE_PATH="$CPLUS_INCLUDE_PATH:$HOME/python3/include/python3.9"
    ./b2 variant=debug -j24 --prefix=$VENV install
    rm -rf bin.v2
    popd
    popd
    touch $BOOST_MARKER
fi

#
# Build Libtorrent and its python bindings
#
pushd $VENV/src
LIBTORRENT_VERSION=1.2.1
LIBTORRENT_MARKER=`build_marker libtorrent $LIBTORRENT_VERSION`
LIBTORRENT_PATHV=`echo $LIBTORRENT_VERSION | sed 's/\./_/g'`
if [ ! -e $VENV/lib/python*/site-packages/libtorrent*.so  -o ! -e $LIBTORRENT_MARKER ]; then
    LIBTORRENT_SRC=libtorrent-rasterbar-$LIBTORRENT_VERSION
    LIBTORRENT_TAR=$LIBTORRENT_SRC.tar.gz
    if [ ! -e $LIBTORRENT_TAR ]; then
        LIBTORRENT_DOWNLOAD_URL=https://github.com/arvidn/libtorrent/releases/download/libtorrent-$LIBTORRENT_PATHV/$LIBTORRENT_TAR
        wget $LIBTORRENT_DOWNLOAD_URL
    fi
    if [ ! -d $LIBTORRENT_SRC ]; then
        tar xavf $LIBTORRENT_TAR
    fi
    pushd $LIBTORRENT_SRC

    # The configuration of libtorrent highly depends on whether we are using Python 2 or Python 3
    PYTHON=$VENV/bin/python CPPFLAGS="-I$VENV/include" LDFLAGS="-L$VENV/lib" ./configure PYTHON_LDFLAGS="-lpython3.9 -lpthread -ldl -lutil -lm" --enable-python-binding --with-boost-python=boost_python37 --with-boost-libdir=$VENV/lib --with-boost=$VENV --prefix=$VENV

    make -j24
    make install
    popd
    popd
    touch $LIBTORRENT_MARKER
fi

# libnacl needs libffi
LIBFFI_VERSION=3.2.1
LIBFFI_MARKER=`build_marker libffi $LIBFFI_VERSION`
if [ ! -e $VENV/lib/libffi-$LIBFFI_VERSION/include/ffi.h -o ! -e $LIBFFI_MARKER ]; then
    LIBFFI_PACKAGE="libffi-$LIBFFI_VERSION.tar.gz"
    if [ ! -e $VENV/src/$LIBFFI_PACKAGE ]; then
        pushd $VENV/src
        wget "ftp://sourceware.org:/pub/libffi/$LIBFFI_PACKAGE"
        popd
    fi

    if [ ! -e $VENV/src/libffi-$LIBFFI_VERSION*/ ]; then
        pushd $VENV/src
        tar axvf $VENV/src/$LIBFFI_PACKAGE
        popd
    fi

    pushd $VENV/src/libffi-$LIBFFI_VERSION*/
    ./configure --prefix=$VENV
    make -j$CONCURRENCY_LEVEL || make
    make install
    popd
    touch $LIBFFI_MARKER
fi

# install libsodium
LIBSODIUM_VERSION=1.0.18
LIBSODIUM_MARKER=`build_marker libsodium $LIBSODIUM_VERSION`
if [ ! -e $VENV/include/sodium.h  -o ! -e $LIBSODIUM_MARKER ]; then
    LIBSODIUM_PACKAGE="libsodium-$LIBSODIUM_VERSION.tar.gz"
    if [ ! -e $VENV/src/$LIBSODIUM_PACKAGE ]; then
        pushd $VENV/src
        wget "https://download.libsodium.org/libsodium/releases/$LIBSODIUM_PACKAGE"
        popd
    fi

    if [ ! -e $VENV/src/libsodium-$LIBSODIUM_VERSION*/ ]; then
        pushd $VENV/src
        tar axvf $VENV/src/$LIBSODIUM_PACKAGE
        popd
    fi

    pushd $VENV/src/libsodium-$LIBSODIUM_VERSION*/
    ./configure --prefix=$VENV
    make -j$CONCURRENCY_LEVEL || make
    make install
    popd
    touch $LIBSODIUM_MARKER
fi

# export PKG_CONFIG_PATH to find libffi and libsodium
export PKG_CONFIG_PATH=$VENV/lib/pkgconfig:$PKG_CONFIG_PATH
export LD_LIBRARY_PATH=$VENV/lib:$LD_LIBRARY_PATH

# CFFI needs to be installed before pynacl or pip will find the older system version and fail to build it...
CFLAGS="$CFLAGS -I$VENV/include" LDFLAGS="$LDFLAGS -L$VENV/lib" pip install --upgrade cffi

echo "
bcrypt
chardet
cherrypy
configobj
cryptography
cython
dnspython
ecdsa
libnacl
lz4
netifaces
networkx
pony
protobuf
psutil
pydantic
pynacl # New EC crypto stuff for tunnelcommunity
pyyaml
pyOpenSSL
qrcode
service_identity
aiohttp
aiohttp_apispec
yappi
orjson
" > ~/requirements.txt

CFLAGS="$CFLAGS -I$VENV/include" LDFLAGS="$LDFLAGS -L$VENV/lib" pip install --upgrade -r ~/requirements.txt

#$VENV/bin/python $VENV/bin/pip install -r ~/requirements.txt\
rm ~/requirements.txt

# pycompile everything before deactivating the venv
find $VENV -iname *.py[oc] -delete
pycompile.py $VENV

deactivate

touch $VENV/.completed.$SCRIPT_VERSION

# Clear some space
rm -rf $VENV/src

echo "Done, you can use this virtualenv with:
	source venv/bin/activate
And exit from it with:
	activate
Enjoy."
