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

if [ ! -z "$VIRTUALENV_DIR" ]; then
    VENV=$VIRTUALENV_DIR
else
    VENV=$HOME/venv
fi

export LD_LIBRARY_PATH=$VENV/lib:$LD_LIBRARY_PATH

if [ -e $VENV/.completed.$SCRIPT_VERSION ]; then
    exit
fi

if [ ! -e $VENV/bin/python ]; then
    PYTHON_BIN=/usr/bin/python
    virtualenv -p $PYTHON_BIN --no-site-packages --system-site-packages --clear $VENV
    $VENV/bin/easy_install --upgrade pip
fi

mkdir -p $VENV/src

source $VENV/bin/activate

# Install apsw manually as it is not available trough pip (well, it is but it's not the official will :)
APSW_VERSION=3.23.1-r1
APSW_MARKER=`build_marker apsw $APSW_VERSION`
if [ ! -e $VENV/lib/python2.*/site-packages/apsw-*.egg -o ! -e $APSW_MARKER ]; then
    pushd $VENV/src
    if [ ! -e apsw-*zip ]; then
        wget https://github.com/rogerbinns/apsw/releases/download/$APSW_VERSION/apsw-$APSW_VERSION.zip
    fi
    if [ ! -d apsw*/src ]; then
        unzip apsw*.zip
    fi
    cd apsw*/
    python setup.py fetch --missing-checksum-ok --all build --enable-all-extensions install
    popd
    touch $APSW_MARKER
fi

# M2Crypto needs OpenSSL with EC support, but RH/Fedora doesn't provide it.
# We install it in a different place so it will not end up in LD_LIBRARY_PATH
# affecting the system's ssh binary.
M2CDEPS=$VENV/m2cdeps
mkdir -p $M2CDEPS

OPENSSL_VERSION=1.0.1h
OPENSSL_MARKER=`build_marker openssl $OPENSSL_VERSION`
if [ ! -e $M2CDEPS/lib/libcrypto.a -o ! -e $OPENSSL_MARKER ]; then
    pushd $VENV/src
    if [ ! -e openssl-$OPENSSL_VERSION*.tar.gz ]; then
        wget --no-check-certificate https://www.openssl.org/source/openssl-$OPENSSL_VERSION.tar.gz
    fi
    if [ ! -d openssl-$OPENSSL_VERSION*/ ]; then
        rm -fR openssl-*/
        tar xvzpf openssl-$OPENSSL_VERSION*tar.gz
    fi
    pushd openssl-$OPENSSL_VERSION*/

    ./config -fPIC -DOPENSSL_PIC --prefix=$M2CDEPS threads no-shared --openssldir=$M2CDEPS/share/openssl
    make -j${CONCURRENCY_LEVEL} || make -j2 || make # Fails when building in multithreaded mode (at least with -j24)
    make depend
    make install_sw
    echo "Done"
    popd
    popd
    touch $OPENSSL_MARKER
fi

M2CRYPTO_VERSION=0.24.0
M2CRYPTO_MARKER=`build_marker m2crypto $M2CRYPTO_VERSION`
if [ ! -e $VENV/lib/python*/site-packages/M2Crypto*.egg  -o ! -e $M2CRYPTO_MARKER ]; then
    pushd $VENV/src
    if [ ! -e M2Crypto-$M2CRYPTO_VERSION*gz ]; then
        wget --no-check-certificate https://pypi.python.org/packages/source/M/M2Crypto/M2Crypto-$M2CRYPTO_VERSION.tar.gz
    fi
    if [ ! -d M2Crypto-$M2CRYPTO_VERSION*/ ]; then
        rm -fR M2Crypto-*/
        tar xvapf M2Crypto-$M2CRYPTO_VERSION*gz
    fi
    pushd M2Crypto-$M2CRYPTO_VERSION*/

    # disable linking against libssl and libcrypto as we are statically linking against it. See openssl build section
    # and the end of this section for a convoluted explanation.
    sed -i 's/self.libraries.*ssl.*crypto.*/self.libraries = []/g' setup.py

    # Add openssl's .a's at THE END of the compile command. Using LDFLAGS won't work as it would end up in the middle.
    EXTRA_LINK_ARGS="-fPIC $M2CDEPS/lib/libssl.a $M2CDEPS/lib/libcrypto.a"
    sed -i 's~\( extra_compile_args=\[.*,$\)~\1 extra_link_args='"'$EXTRA_LINK_ARGS'.split()"',~' setup.py

    # python setup.py clean # This doesn't clean everything
    rm -fR build # this does
    #python setup.py build || : # Do not run this, it will break the proper stuff made by build_ext
    python setup.py build_py
    # This should use our custom libcrypto (explicit RPATH) (It doesn't matter anymore as we are statically linking)
    python setup.py --verbose build_ext --openssl=$M2CDEPS --rpath=$M2CDEPS/lib --include-dirs=$M2CDEPS/include

    python setup.py install
    popd

    echo "Testing if the EC stuff is working..."
    python -c 'import M2Crypto as m; m.EC.gen_params(m.m2.NID_sect409k1)'

    touch $M2CRYPTO_MARKER
fi

# Build libboost
BOOST_VERSION=1.58.0
BOOST_MARKER=`build_marker boost $BOOST_VERSION`
BOOST_PATHV=`echo $BOOST_VERSION | sed 's/\./_/g'`
if [ ! -e $VENV/src/boost_$BOOST_PATHV/bjam -o ! -e $VENV/lib/libboost_python.so -o ! -e $BOOST_MARKER ]; then
    pushd $VENV/src
    BOOST_TAR=boost_$BOOST_PATHV.tar.bz2
    if [ ! -e $BOOST_TAR ]; then
        wget http://netcologne.dl.sourceforge.net/project/boost/boost/$BOOST_VERSION/$BOOST_TAR
    fi
    if [ ! -e boost_$BOOST_PATHV ]; then
        tar xavf $BOOST_TAR
    fi

    cd boost_$BOOST_PATHV/

    ./bootstrap.sh
    ./b2 -j$CONCURRENCY_LEVEL --prefix=$VENV install
    popd
    touch $BOOST_MARKER
fi



#
# Build Libtorrent and its python bindings
#
pushd $VENV/src
LIBTORRENT_VERSION=1.1.0
LIBTORRENT_MARKER=`build_marker libtorrent $LIBTORRENT_VERSION`
LIBTORRENT_PATHV=`echo $LIBTORRENT_VERSION | sed 's/\./_/g'`
if [ ! -e $VENV/lib/python*/site-packages/libtorrent.so  -o ! -e $LIBTORRENT_MARKER ]; then
    LIBTORRENT_SRC=libtorrent-rasterbar-$LIBTORRENT_VERSION
    LIBTORRENT_TAR=$LIBTORRENT_SRC.tar.gz
    if [ ! -e $LIBTORRENT_TAR ]; then
        wget https://github.com/arvidn/libtorrent/releases/download/libtorrent-1_1/$LIBTORRENT_TAR
    fi
    if [ ! -d $LIBTORRENT_SRC ]; then
        tar xavf $LIBTORRENT_TAR
    fi
    pushd $LIBTORRENT_SRC
    export BOOST_ROOT=$VENV/src/boost_$BOOST_PATHV
    $BOOST_ROOT/bjam -j$CONCURRENCY_LEVEL --prefix=$VENV install
    pushd bindings/python
    $BOOST_ROOT/bjam -j$CONCURRENCY_LEVEL --prefix=$VENV
    popd
    pushd $VENV/lib
    ln -fs libboost_python.so libboost_python-py27.so.$LIBTORRENT_VERSION
    cp $VENV/src/libtorrent-rasterbar-$LIBTORRENT_VERSION/bindings/python/bin/*/*/libtorrent-python-*/*/libtorrent.so $VENV/lib/python2.7/site-packages/
    popd
    popd
    # Check that the modules work
    python -c "import libtorrent"
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
MPFR_VERSION=4.0.1
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
configobj
cryptography
cython
datrie
dnspython
ecdsa
jsonrpclib
meliae
netifaces
networkx
pbkdf2
protobuf
psutil
pyaes
pyasn1 # for twisted
pycrypto # Twisted needs it
pynacl # New EC crypto stuff for tunnelcommunity
PySocks
pysqlite
qrcode
service_identity
six
twisted
validate
" > ~/requirements.txt

CFLAGS="$CFLAGS -I$VENV/include" LDFLAGS="$LDFLAGS -L$VENV/lib" pip install --upgrade -r ~/requirements.txt

#$VENV/bin/python $VENV/bin/pip install -r ~/requirements.txt\
rm ~/requirements.txt

# pycompile everything before deactivating the venv
find $VENV -iname *.py[oc] -delete
pycompile.py $VENV

deactivate

virtualenv --relocatable $VENV

#rm -fR venv
#mv $VENV $VENV/../venv
rm -fR build-tmp

touch $VENV/.completed.$SCRIPT_VERSION

echo "Done, you can use this virtualenv with:
	source venv/bin/activate
And exit from it with:
	activate
Enjoy."

#
# setup_env.sh ends here
