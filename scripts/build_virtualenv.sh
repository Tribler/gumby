#!/bin/bash
# setup_env.sh ---
#
# Filename: setup_env.sh
# Description:
# Author: Elric Milon
# Maintainer:
# Created: Wed May 22 19:18:49 2013 (+0200)

# Commentary:
#
# %*% Builds a virtualenv with everything necessary to run Tribler/IPv8. Can be safely executed every time the
# %*% experiment is run as it will detect if the environment is up to date and exit if there's nothing to do.
#
#

# Change Log:
#
#
#
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street, Fifth
# Floor, Boston, MA 02110-1301, USA.
#
#

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

if [[ $* == *--py3* ]]; then
    DEFAULT_VENV_DIR_NAME="venv3"
else
    DEFAULT_VENV_DIR_NAME="venv"
fi

if [ ! -z "$VIRTUALENV_DIR" ]; then
    VENV=$VIRTUALENV_DIR
else
    VENV=$HOME/$DEFAULT_VENV_DIR_NAME
fi

export LD_LIBRARY_PATH=$VENV/lib:$LD_LIBRARY_PATH

if [ -e $VENV/.completed.$SCRIPT_VERSION ]; then
    exit
fi

# If we compile for Python 3, we want to install a newer version since the version on the DAS5 is outdated.
if [[ $* == *--py3* ]] && [ ! -e ~/python3/bin/python3 ]; then
    pushd $HOME
    wget https://www.python.org/ftp/python/3.7.3/Python-3.7.3.tgz
    tar -xzvf Python-3.7.3.tgz
    pushd Python-3.7.3
    ./configure --prefix=$PWD/../python3
    make install -j24
    popd
    popd
fi

if [[ $* == *--py3* ]]; then
    export PATH=$HOME/python3/bin:$PATH
fi

python -v

if [ ! -e $VENV/bin/python ]; then
    if [[ $* == *--py3* ]]; then
        PYTHON_BIN=$HOME/python3/bin
        python3 -m venv --system-site-packages --clear $VENV
    else
        PYTHON_BIN=/usr/bin/python
        virtualenv -p $PYTHON_BIN --no-site-packages --system-site-packages --clear $VENV
    fi

    $VENV/bin/easy_install --upgrade pip
fi

mkdir -p $VENV/src

source $VENV/bin/activate

#
# Build boost (if using Python 3, otherwise use system boost)
#
if [[ $* == *--py3* ]]; then
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
            tar -xzvf $BOOST_TAR
        fi
        pushd $BOOST_SRC
        ./bootstrap.sh
        export CPLUS_INCLUDE_PATH="$CPLUS_INCLUDE_PATH:$HOME/python3/include/python3.7m"
        ./b2 variant=debug -j24 --prefix=$VENV install
        rm -rf bin.v2
        popd
        popd
        touch $BOOST_MARKER
    fi
fi

#
# Build Libtorrent and its python bindings
#
pushd $VENV/src
if [[ $* == *--py3* ]]; then
    LIBTORRENT_VERSION=1.2.1
else
    # For Python 2, we use an older version of libtorrent so we do not have to compile a newer version of Boost ourselves.
    LIBTORRENT_VERSION=1.1.12
fi
LIBTORRENT_MARKER=`build_marker libtorrent $LIBTORRENT_VERSION`
LIBTORRENT_PATHV=`echo $LIBTORRENT_VERSION | sed 's/\./_/g'`
if [ ! -e $VENV/lib/python*/site-packages/libtorrent*.so  -o ! -e $LIBTORRENT_MARKER ]; then
    LIBTORRENT_SRC=libtorrent-rasterbar-$LIBTORRENT_VERSION
    LIBTORRENT_TAR=$LIBTORRENT_SRC.tar.gz
    if [ ! -e $LIBTORRENT_TAR ]; then
        if [[ $* == *--py3* ]]; then
            LIBTORRENT_DOWNLOAD_URL=https://github.com/arvidn/libtorrent/releases/download/libtorrent-$LIBTORRENT_PATHV/$LIBTORRENT_TAR
        else
            # Slightly different format of the download URL for older version of libtorrent...
            LIBTORRENT_DOWNLOAD_URL=https://github.com/arvidn/libtorrent/releases/download/libtorrent_$LIBTORRENT_PATHV/$LIBTORRENT_TAR
        fi
        wget $LIBTORRENT_DOWNLOAD_URL
    fi
    if [ ! -d $LIBTORRENT_SRC ]; then
        tar xavf $LIBTORRENT_TAR
    fi
    pushd $LIBTORRENT_SRC

    # The configuration of libtorrent highly depends on whether we are using Python 2 or Python 3
    if [[ ! $* == *--py3* ]]; then
        ./configure --enable-python-binding --prefix=$VENV
    else
        PYTHON=$VENV/bin/python CPPFLAGS="-I$VENV/include" LDFLAGS="-L$VENV/lib" ./configure PYTHON_LDFLAGS="-lpython3.7m -lpthread -ldl -lutil -lm" --enable-python-binding --with-boost-python=boost_python37 --with-boost-libdir=$VENV/lib --with-boost=$VENV --prefix=$VENV
    fi

    make -j24
    make install
    popd
    popd
    touch $LIBTORRENT_MARKER
fi

# recent libgmp needed by gmpy2 + pycrypto
GMP_VERSION=6.1.2
GMP_MARKER=`build_marker gmp $GMP_VERSION`
if [ ! -e $VENV/include/gmp.h  -o ! -e $GMP_MARKER ]; then

    if [ ! -e $VENV/src/gmp-$GMP_VERSION.tar.bz2 ]; then
        pushd $VENV/src
        wget "ftp://ftp.gmplib.org/pub/gmp-$GMP_VERSION/gmp-$GMP_VERSION.tar.bz2"
        popd
    fi

    if [ ! -e $VENV/src/gmp-$GMP_VERSION*/ ]; then
        pushd $VENV/src
        tar axvf $VENV/src/gmp-$GMP_VERSION.tar.bz2
        popd
    fi

    pushd $VENV/src/gmp-$GMP_VERSION*/
    ./configure --prefix=$VENV
    make -j$CONCURRENCY_LEVEL || make
    make install
    popd
    touch $GMP_MARKER
fi

# libmpfr needed by gmpy2
MPFR_VERSION=4.0.2
MPFR_MARKER=`build_marker mpfr $MPFR_VERSION`
if [ ! -e $VENV/include/mpfr.h  -o ! -e $MPFR_MARKER ]; then

    if [ ! -e $VENV/src/mpfr-$MPFR_VERSION.tar.bz2 ]; then
        pushd $VENV/src
        wget https://www.mpfr.org/mpfr-current/mpfr-$MPFR_VERSION.tar.bz2
        popd
    fi

    if [ ! -e $VENV/src/mpfr-$MPFR_VERSION*/ ]; then
        pushd $VENV/src
        tar axvf $VENV/src/mpfr-$MPFR_VERSION.tar.bz2
        popd
    fi

    pushd $VENV/src/mpfr-$MPFR_VERSION*/
    ./configure --prefix=$VENV --with-gmp-lib=$VENV/lib --with-gmp-include=$VENV/include
    make -j$CONCURRENCY_LEVEL || make
    make install
    popd
    touch $MPFR_MARKER
fi

# libmpc needed by gmpy2
MPC_VERSION=1.1.0
MPC_MARKER=`build_marker mpc $MPC_VERSION`
if [ ! -e $VENV/include/mpc.h  -o ! -e $MPC_MARKER ]; then

    if [ ! -e $VENV/src/mpc-$MPC_VERSION.tar.gz ]; then
        pushd $VENV/src
        wget https://ftp.gnu.org/gnu/mpc/mpc-$MPC_VERSION.tar.gz
        popd
    fi

    if [ ! -e $VENV/src/mpc-$MPC_VERSION*/ ]; then
        pushd $VENV/src
        tar xzvf $VENV/src/mpc-$MPC_VERSION.tar.gz
        popd
    fi

    pushd $VENV/src/mpc-$MPC_VERSION*/
    ./configure --prefix=$VENV --with-gmp-lib=$VENV/lib --with-gmp-include=$VENV/include --with-mpfr-lib=$VENV/lib --with-mpfr-include=$VENV/include
    make -j$CONCURRENCY_LEVEL || make
    make install
    popd
    touch $MPC_MARKER
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
LIBSODIUM_VERSION=1.0.16
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

easy_install pip

# CFFI needs to be installed before pynacl or pip will find the older system version and faild to build it...
CFLAGS="$CFLAGS -I$VENV/include" LDFLAGS="$LDFLAGS -L$VENV/lib" pip install --upgrade cffi

# Gmpy2 requires libgmp, libmpfr and libmpc
CFLAGS="$CFLAGS -I$VENV/include" LDFLAGS="$LDFLAGS -L$VENV/lib" pip install --upgrade gmpy2

echo "
asyncssh
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
pynacl # New EC crypto stuff for tunnelcommunity
pyyaml
pyOpenSSL
qrcode
service_identity
aiohttp
aiohttp_apispec
yappi
" > ~/requirements.txt

# Meliae only works under Python 2
if [[ ! $* == *--py3* ]]; then
    echo "meliae
pysqlite
    " > ~/requirements.txt
fi

CFLAGS="$CFLAGS -I$VENV/include" LDFLAGS="$LDFLAGS -L$VENV/lib" pip install --upgrade -r ~/requirements.txt

#$VENV/bin/python $VENV/bin/pip install -r ~/requirements.txt\
rm ~/requirements.txt

# pycompile everything before deactivating the venv
find $VENV -iname *.py[oc] -delete
pycompile.py $VENV

deactivate

virtualenv --relocatable $VENV

touch $VENV/.completed.$SCRIPT_VERSION

# Clear some space
rm -rf $VENV/src

echo "Done, you can use this virtualenv with:
	source venv/bin/activate
And exit from it with:
	activate
Enjoy."

#
# setup_env.sh ends here
