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
# %*% Builds a virtualenv with everything necessary to run Tribler/Dispersy.  If dtrace is available in the system, it
# %*% also builds SystemTap and a SystemTap-enabled python 2.7 environment.  Can be safely executed every time the
# %*% experiment is run as it will detect if the environment is up to date and exit if there's nothing to do.  Be aware
# %*% that due to SystemTap needing root permissions, the first run of the script will fail giving instructions to the
# %*% user on how to manually run a couple of commands as root to give the necessary privileges to its binaries.
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
SCRIPT_VERSION=17

# Code:
set -e

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

export LD_LIBRARY_PATH=$VENV/inst/lib:$VENV/lib:$LD_LIBRARY_PATH

# Build the systemtap enabled python runtime and systemtap itself
# if dtrace is available, if not, just build python 2.7
if [ ! -e $VENV/inst/.completed.$SCRIPT_VERSION ]; then

    echo "If you get any build problems, please, make sure you have all the required deps:

    For SystemTap & co.:
      sudo apt-get build-dep systemtap
      sudo apt-get install libncurses-dev systemtap-sdt-dev:

    For WX:
      sudo apt-get build-dep wxwidgets2.8
      sudo apt-get install libpangox-1.0-dev

"
    mkdir -p $VENV/src
    pushd $VENV/src
    if [ -e /usr/bin/dtrace ]; then
        WITH_SYSTEMTAP=yes
        EXTRA_CONFIG_OPTS=--with-dtrace
    else
        EXTRA_CONFIG_OPTS=--without-dtrace
    fi


    if [ "$WITH_SYSTEMTAP" == yes ]; then
        if [ ! -e libdwarf-*gz ]; then
            wget http://pkgs.fedoraproject.org/repo/pkgs/libdwarf/libdwarf-20130207.tar.gz/64b42692e947d5180e162e46c689dfbf/libdwarf-20130207.tar.gz
        fi

        if [ ! -d libdwarf-*/ ]; then
            tar xavf libdwarf-*gz
        fi

        if [ ! -e $VENV/inst/lib/libdwarf.so ]; then
            pushd dwarf-*/libdwarf/
            ./configure --prefix=$VENV/inst  --enable-shared
            make -j$(grep process /proc/cpuinfo | wc -l)
            mkdir -p $VENV/inst/lib $VENV/inst/include
            cp libdwarf.h dwarf.h $VENV/inst/include/
            cp libdwarf.so $VENV/inst/lib/
            popd
        fi

        # Build Dyininst (Systemtap dependency)
        if [ ! -e DyninstAPI-*tgz ]; then
            wget http://www.dyninst.org/sites/default/files/downloads/dyninst/8.1.2/DyninstAPI-8.1.2.tgz
        fi
        if [ ! -e DyninstAPI-*/ ]; then
            tar xavf DyninstAPI-*tgz
        fi
        pushd DyninstAPI-*/
        ./configure --prefix=$VENV/inst -with-libdwarf-incdir=$VENV/inst/include --with-libdwarf-libdir=$VENV/inst/lib
        #make -j$(grep process /proc/cpuinfo | wc -l)
        make
        make install
        popd

        # Build systemtap
        # remove old versions of systemtap
        rm -fR systemtap-2.2*

        if [ ! -d systemtap-*/ ]; then
        	if [ ! -e systemtap-*.gz ]; then
                wget http://sourceware.org/systemtap/ftp/releases/systemtap-2.4.tar.gz
            fi
            tar xavf systemtap-*.gz
        fi

        pushd systemtap-*/
        ./configure --prefix=$VENV/inst --with-dyninst=$VENV/inst/
        make -j$(grep process /proc/cpuinfo | wc -l)
        make install
        popd
    fi

    if [ ! -e $VENV/src/cpython-2011 ]; then
        hg clone http://hg.jcea.es/cpython-2011
    fi

    if [ ! -e $VENV/inst/bin/python ]; then
        pushd cpython-2011
        hg checkout dtrace-issue13405_2.7
        LDFLAGS="-Wl,-rpath=$VENV/inst/lib" ./configure $EXTRA_CONFIG_OPTS --prefix=$VENV/inst --enable-shared
        cp Modules/Setup.dist Modules/Setup
        make -j$(grep process /proc/cpuinfo | wc -l)
        make install
        popd
    fi
    touch $VENV/inst/.completed.$SCRIPT_VERSION
    popd
fi

if [ -e $VENV/.completed.$SCRIPT_VERSION ]; then
    exit
fi

# Build libevent, not really needed for anything python related, but swift
# needs a newer version than the one installed on the DAS4
if [ ! -e $VENV/inst/lib/libevent.so ]; then
    pushd $VENV/src
    if [ ! -e libevent-*tar.gz ]; then
        wget https://github.com/downloads/libevent/libevent/libevent-2.0.21-stable.tar.gz
    fi
    if [ ! -e libevent-*/ ]; then
        tar xapf libevent-*.tar.gz
    fi
    cd libevent-*/
    ./configure --prefix=$VENV/inst
    make -j$(grep process /proc/cpuinfo | wc -l)
    make install
    popd
fi

if [ ! -e $VENV/bin/python ]; then
    #virtualenv   --no-site-packages --clear $VENV
    virtualenv -p $VENV/inst/bin/python --no-site-packages --system-site-packages --clear $VENV
    $VENV/bin/easy_install --upgrade pip
fi

mkdir -p $VENV/src

source $VENV/bin/activate


# Install apsw manually as it is not available trough pip.
if [ ! -e $VENV/lib/python2.*/site-packages/apsw.so ]; then
    pushd $VENV/src
    if [ ! -e apsw-*zip ]; then
        wget https://apsw.googlecode.com/files/apsw-3.7.16.2-r1.zip
    fi
    if [ ! -d apsw*/src ]; then
        unzip apsw*.zip
    fi
    cd apsw*/
    # Fix a bug on apsw's setup.py
    sed -i "s/part=part.split('=', 1)/part=tuple(part.split('=', 1))/" setup.py
    python setup.py fetch --missing-checksum-ok --all --version=3.7.17 build --enable-all-extensions install # test # running the tests makes it segfault...
    popd
fi

# M2Crypto needs OpenSSL with EC support, but RH/Fedora doesn't provide it.
# We install it in a different place so it will not end up in LD_LIBRARY_PATH
# affecting the system's ssh binary.
M2CDEPS=$VENV/m2cdeps
mkdir -p $M2CDEPS
if [ ! -e $M2CDEPS/lib/libcrypto.a ]; then
    pushd $VENV/src
    if [ ! -e openssl-*.tar.gz ]; then
        #wget --no-check-certificate https://www.openssl.org/source/openssl-1.0.1e.tar.gz
        wget --no-check-certificate https://www.openssl.org/source/openssl-1.0.1f.tar.gz
    fi
    if [ ! -d openssl-*/ ]; then
        tar xvzpf openssl*tar.gz
    fi
    pushd openssl-*/

    ./config -fPIC --prefix=$M2CDEPS threads --openssldir=$M2CDEPS/share/openssl
    make -j2 || make #Fails when building in multithreaded mode (at least with -j24)
    make install_sw
    # Proper names for M2Crypto
    #ln -sf $M2CDEPS/lib/libssl.so.1.0.0 $M2CDEPS/lib/libssl.so.10
    #ln -sf $M2CDEPS/lib/libcrypto.so.1.0.0 $M2CDEPS/lib/libcrypto.so.10
    echo "Done"
    popd
    popd
fi

if [ ! -e $VENV/lib/python*/site-packages/M2Crypto*.egg ]; then
    pushd $VENV/src
    if [ ! -e M2Crypto-*gz ]; then
        wget --no-check-certificate http://pypi.python.org/packages/source/M/M2Crypto/M2Crypto-0.21.1.tar.gz
    fi
    if [ ! -d M2Crypto-*/ ]; then
        tar xvapf M2Crypto-*.tar.gz
    fi
    pushd M2Crypto-*/
    # python setup.py clean # This does nothing
    #rm -fR build # this does :D
    #python setup.py build || : # Do not run this, it will break the proper stuff made by build_ext
    python setup.py build_py
    # This should use our custom libcrypto (explicit RPATH)
    CFLAGS="$M2CDEPS/lib/libcrypto.a -fPIC" python setup.py --verbose build_ext --openssl=$M2CDEPS --rpath=$M2CDEPS/lib --include-dirs=$M2CDEPS/include
    python setup.py install
    popd
fi

echo "Testing if the EC stuff is working..."
python -c "from M2Crypto import EC"

#Not sure if we need this:
#pushd build-tmp
#wget http://download.zeromq.org/zeromq-3.2.3.tar.gz
#tar xvzpf zeromq*tar.gz
#cd zeromq*/
#./configure --prefix=$VIRTUAL_ENV
#make -j$(grep processor /proc/cpuinfo | wc -l)
#popd


# Build libboost
# TODO(vladum): If you use this, see TODO about libtorrent's bug.
 if [ ! -e $VENV/lib/libboost_wserialization.so ]; then
     pushd $VENV/src
     BOOST_TAR=boost_1_54_0.tar.bz2
    if [ ! -e $BOOST_TAR ]; then
        wget http://netcologne.dl.sourceforge.net/project/boost/boost/1.54.0/$BOOST_TAR
    fi
    tar xavf $BOOST_TAR
     cd boost*/
     ./bootstrap.sh
     #./b2 -j$(grep process /proc/cpuinfo | wc -l) --prefix=$VENV install
     ./bjam -j$(grep process /proc/cpuinfo | wc -l) threading=multi -no_single -no_static --without-mpi --prefix=$VENV install
     popd
 fi


#
# Build Libtorrent and its python bindings
#
pushd $VENV/src
if [ ! -e $VENV/lib/python*/site-packages/libtorrent.so ]; then
    LIBTORRENT_SRC=libtorrent-rasterbar-0.16.15
    LIBTORRENT_TAR=$LIBTORRENT_SRC.tar.gz
    if [ ! -e $LIBTORRENT_TAR ]; then
        wget --no-check-certificate http://downloads.sourceforge.net/project/libtorrent/libtorrent/$LIBTORRENT_TAR
    fi
    if [ ! -d $LIBTORRENT_SRC ]; then
        tar xavf $LIBTORRENT_TAR
    fi
    cd $LIBTORRENT_SRC
    # TODO(vladum): libtorrent uses boost::system::get_system_category() in a
    # few places, instead of their get_system_category() wrapper. This method
    # has been renamed in version 1.43.0 to boost::system::system_category().
    # Using a newer Boost requires patching libtorrent, so, for now, we will use
    # the system's Boost, which is 1.41.0 on DAS4 and works fine.
    export BOOST_ROOT=$VENV/src/boost_*/
    ./configure  --with-boost-system=mt --with-boost=$VENV --with-boost-lib=$VENV/lib --enable-python-binding --prefix=$VENV
    make -j$(grep process /proc/cpuinfo | wc -l) || make
    make install
    cd $VENV/lib
    # TODO(vladum): Uncomment for custom Boost, but see upper comment.
    ln -fs libboost_python.so libboost_python-py27.so.1.54.0
    cd ../..
fi

# wxpython
pushd $VENV/src
if [ ! -e wxPython-*.tar.bz2 ]; then
    wget http://garr.dl.sourceforge.net/project/wxpython/wxPython/2.8.12.1/wxPython-src-2.8.12.1.tar.bz2
fi
if [ ! -d wxPython*/ ]; then
    tar xavf wxPython-*.tar.bz2
fi
pushd wxPython*/
if [ ! -e $VENV/lib/libwx_gtk2u_gizmos_xrc-*.so ]; then
    make uninstall ||:
    make clean ||:
    ./configure --prefix=$VENV \
        --enable-display \
        --enable-geometry \
        --enable-graphics_ctx \
        --enable-sound \
        --enable-unicode \
        --with-gtk \
        --with-libjpeg=sys \
        --with-libpng=sys \
        --with-libtiff=builtin \
        --with-sdl \
        --with-zlib=sys \
        --without-gnomeprint \
        --without-opengl \
        --with-expat=sys
    # TODO(emilon): Are those CFLAGS needed?
    CFLAGS="-Iinclude" make -j$(grep process /proc/cpuinfo | wc -l) || CFLAGS="-Iinclude" make
    make install
    pushd contrib
    make -j$(grep process /proc/cpuinfo | wc -l) || make
    make install
    popd
fi
pwd

if [ ! -e $VENV/lib/python*/site-packages/wx-*/wxPython/_wx.py ]; then
    pushd wxPython
    python setup.py build BUILD_GLCANVAS=0 #BUILD_STC=0
    python setup.py install BUILD_GLCANVAS=0 #BUILD_STC=0
    popd
fi
popd

# recent libgmp needed by pycrypto
if [ ! -e $VENV/src/gmp-5.1.3.tar.bz2 ]; then
    pushd $VENV/src
    wget "ftp://ftp.gmplib.org/pub/gmp-5.1.3/gmp-5.1.3.tar.bz2"
    popd
fi

if [ ! -e $VENV/src/gmp-*/ ]; then
    pushd $VENV/src
    tar axvf $VENV/src/gmp-5.1.3.tar.bz2
    popd
fi

if [ ! -e $VENV/include/gmp.h ]; then
    pushd $VENV/src/gmp-*/
    ./configure --prefix=$VENV
    make -j$(grep process /proc/cpuinfo | wc -l) || make
    make install
    popd
fi

# libnacl needs libffi
LIBFFI_PACKAGE="libffi-3.0.11.tar.gz"
if [ ! -e $VENV/src/$LIBFFI_PACKAGE ]; then
    pushd $VENV/src
    wget "ftp://sourceware.org:/pub/libffi/$LIBFFI_PACKAGE"
    popd
fi

if [ ! -e $VENV/src/libffi-*/ ]; then
    pushd $VENV/src
    tar axvf $VENV/src/$LIBFFI_PACKAGE
    popd
fi

if [ ! -e $VENV/include/ffi.h ]; then
    pushd $VENV/src/libffi-*/
    ./configure --prefix=$VENV
    make -j$(grep process /proc/cpuinfo | wc -l) || make
    make install
    popd
fi

# install libsodium
LIBSODIUM_PACKAGE="libsodium-1.0.2.tar.gz"
if [ ! -e $VENV/src/$LIBSODIUM_PACKAGE ]; then
    pushd $VENV/src
    wget "https://download.libsodium.org/libsodium/releases/$LIBSODIUM_PACKAGE"
    popd
fi

if [ ! -e $VENV/src/libsodium-*/ ]; then
    pushd $VENV/src
    tar axvf $VENV/src/$LIBSODIUM_PACKAGE
    popd
fi

if [ ! -e $VENV/include/sodium.h ]; then
    pushd $VENV/src/libsodium-*/
    ./configure --prefix=$VENV
    make -j$(grep process /proc/cpuinfo | wc -l) || make
    make install
    popd
fi

# export PKG_CONFIG_PATH to find libffi and libsodium
export PKG_CONFIG_PATH=$VENV/lib/pkgconfig:$PKG_CONFIG_PATH
export LD_LIBRARY_PATH=$VENV/lib:$LD_LIBRARY_PATH

# remove pil cause its a piece of crap
rm -f $VENV/bin/pil*
rm -rf $VENV/lib/python2.7/site-packages/PIL

#pip install --upgrade pip

sed -i 's~#!/usr/bin/env python2.6~#!/usr/bin/env python~' $VENV/bin/*
easy_install pip

echo "
Jinja2 # Used for systemtap report generation scripts from Cor-Paul
configobj
cython
gmpy==1.16
ipython
nose
nosexcover
ntplib
pillow
psutil
pyasn1 # for twisted
pycrypto # Twisted needs it
pysqlite
pyzmq
twisted # Used by the config server/clients
unicodecsv # used for report generation scripts from Cor-Paul
pynacl # New EC crypto stuff for tunnelcommunity
cffi
pycparser
six
cryptography
" > ~/requirements.txt

# For some reason the pip scripts get a python 2.6 shebang, fix it.
sed -i 's~#!/usr/bin/env python2.6~#!/usr/bin/env python~' $VENV/bin/pip*

# numpy # used for report generation scripts from Cor-Paul, installed all by itself as it fails to build if we pass CFLAGS & co.
pip install numpy

# install netifaces separately because it requires some params now
pip install netifaces --allow-external netifaces --allow-unverified netifaces

CFLAGS="$CFLAGS -I$VENV/include" LDFLAGS="$LDFLAGS -L$VENV/lib" pip install -r ~/requirements.txt

# meliae is not on the official repos
pip install --allow-unverified pyrex --allow-external  pyrex pyrex
pip install --allow-unverified meliae --allow-external meliae meliae

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

if [ ! -e $VENV/inst/bin/staprun -o -u $VENV/inst/bin/staprun -a $(stat -c %U staprun 2> /dev/null)==root ]; then
    touch $VENV/.completed.$SCRIPT_VERSION
else
    echo " Please, run those commands as root and re-run the setup script."
    echo "   chown root $VENV/inst/bin/staprun"
    echo "   chmod +s   $VENV/inst/bin/staprun"
    exit 100
fi

echo "Done, you can use this virtualenv with:
	source venv/bin/activate
And exit from it with:
	activate
Enjoy."

#
# setup_env.sh ends here
