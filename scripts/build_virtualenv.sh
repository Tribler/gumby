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
SCRIPT_VERSION=22

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
    # @CONF_OPTION WITH_SYSTEMTAP: Build a python interpreter and needed tools with systemtap support, "true"
    # @CONF_OPTION WITH_SYSTEMTAP: enables if /usr/bin/dtrace is available (default: false)
    mkdir -p $VENV/src
    pushd $VENV/src
    if [ -e /usr/bin/dtrace -a "${WITH_SYSTEMTAP,,}" == true ]; then
        WITH_SYSTEMTAP=true
        EXTRA_CONFIG_OPTS=--with-dtrace
    else
        EXTRA_CONFIG_OPTS=--without-dtrace
    fi


    if [ "$WITH_SYSTEMTAP" == "true" ]; then
        if [ ! -e libdwarf-*gz ]; then
            wget http://pkgs.fedoraproject.org/repo/pkgs/libdwarf/libdwarf-20130207.tar.gz/64b42692e947d5180e162e46c689dfbf/libdwarf-20130207.tar.gz
        fi

        if [ ! -d libdwarf-*/ ]; then
            tar xavf libdwarf-*gz
        fi

        if [ ! -e $VENV/inst/lib/libdwarf.so ]; then
            pushd dwarf-*/libdwarf/
            ./configure --prefix=$VENV/inst  --enable-shared
            make -j$CONCURRENCY_LEVEL
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
        make -j$CONCURRENCY_LEVEL || make
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
        make -j$CONCURRENCY_LEVEL
        make install
        popd

        if [ ! -e $VENV/src/cpython-2011 ]; then
            hg clone http://hg.jcea.es/cpython-2011
        fi

        if [ ! -e $VENV/inst/bin/python ]; then
            pushd cpython-2011
            hg checkout dtrace-issue13405_2.7
            if ! ( python -c 'import sys; print(sys.maxunicode)' | grep -q '65535' ); then
                EXTRA_CONFIG_OPTS="$EXTRA_CONFIG_OPTS --enable-unicode=ucs4"
            fi
            LDFLAGS="-Wl,-rpath=$VENV/inst/lib" ./configure $EXTRA_CONFIG_OPTS --prefix=$VENV/inst --enable-shared
            cp Modules/Setup.dist Modules/Setup
            make -j$CONCURRENCY_LEVEL
            make install
            popd
        fi
        touch $VENV/inst/.completed.$SCRIPT_VERSION
        popd
    fi
fi

if [ -e $VENV/.completed.$SCRIPT_VERSION ]; then
    exit
fi

# DISABLED: We don't use swift anymore
# Build libevent, not really needed for anything python related, but swift
# needs a newer version than the one installed on the DAS4
# if [ ! -e $VENV/inst/lib/libevent.so ]; then
#     pushd $VENV/src
#     if [ ! -e libevent-*tar.gz ]; then
#         wget https://github.com/downloads/libevent/libevent/libevent-2.0.21-stable.tar.gz
#     fi
#     if [ ! -e libevent-*/ ]; then
#         tar xapf libevent-*.tar.gz
#     fi
#     cd libevent-*/
#     ./configure --prefix=$VENV/inst
#     make -j$CONCURRENCY_LEVEL
#     make install
#     popd
# fi


if [ ! -e $VENV/bin/python ]; then
    #virtualenv   --no-site-packages --clear $VENV
    if [ "$WITH_SYSTEMTAP" == "true" ]; then
        PYTHON_BIN=$VENV/inst/bin/python
    else
        PYTHON_BIN=/usr/bin/python
    fi

    virtualenv -p $PYTHON_BIN --no-site-packages --system-site-packages --clear $VENV
    $VENV/bin/easy_install --upgrade pip
fi

mkdir -p $VENV/src

source $VENV/bin/activate


# Install apsw manually as it is not available trough pip (well, it is but it's not the official will :)
APSW_VERSION=3.12.2-r1
APSW_MARKER=`build_marker apsw $APSW_VERSION`
if [ ! -e $VENV/lib/python2.*/site-packages/apsw.so -o ! -e $APSW_MARKER ]; then
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
    touch $APSW_MARKER
fi

# M2Crypto needs OpenSSL with EC support, but RH/Fedora doesn't provide it.
# We install it in a different place so it will not end up in LD_LIBRARY_PATH
# affecting the system's ssh binary.
M2CDEPS=$VENV/m2cdeps
mkdir -p $M2CDEPS

OPENSSL_VERSION=1.0.1h
OPENSSL_MARKER=`build_marker openssl $OPENSSL_VERSION`
if [ ! -e $M2CDEPS/lib/libcrypto.so.1.0.0  -o ! -e $OPENSSL_MARKER ]; then
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
    make -j${CONCURRENCY_LEVEL} || make -j2 || make #Fails when building in multithreaded mode (at least with -j24)
    make depend
    make install_sw
    # Disabled as we are statically linking now to avoid breaking openssl and requiring M2Crypto to be imported before
    # anything using openssl to work around the fact that, as m2crypto is the only module linking against the custom
    # build openssl. If some other module imports the system openssl, m2crypto's dependency will be satisfied and will
    # break when trying to use one of de disabled curves.

    # Proper names for M2Crypto (m2crypto will be linked against this soname and and will have the RPATH set to M2CDEPS/libs)
    # ln -sf $M2CDEPS/lib/libssl.so.$OPENSSL_VERSION $M2CDEPS/lib/libssl.so.10
    # ln -sf $M2CDEPS/lib/libcrypto.so.$OPENSSL_VERSION $M2CDEPS/lib/libcrypto.so.10
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
        wget --no-check-certificate http://pypi.python.org/packages/source/M/M2Crypto/M2Crypto-$M2CRYPTO_VERSION.tar.gz
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
    # How the gcc command should look when building m2crypto:
    # gcc -pthread -shared -Wl,-z,relro -fPIC build/temp.linux-x86_64-2.7/SWIG/_m2crypto_wrap.o -L/usr/lib64
    # -L/home/pouwelse/venv/m2cdeps/lib -Wl,-R/home/pouwelse/venv/m2cdeps/lib -lpython2.7 -o
    # build/lib.linux-x86_64-2.7/M2Crypto/__m2crypto.so /home/pouwelse/venv/m2cdeps/lib/libssl.a
    # /home/pouwelse/venv/m2cdeps/lib/libcrypto.a
    #
    # Note that -lssl -lcrypto are gone and that bith libssl.a and libcrypto.a are AT THE END of the command. Otherwise
    # symbols will be missing: undefined symbol: i2d_X509
    #
    # Also note that the .a ordering is important, putting libcrypto first will produce missing symbols.
    #
    # For instance, this will fail:
    # gcc -pthread -shared -Wl,-z,relro -fPIC /home/pouwelse/venv/m2cdeps/lib/libssl.a
    # /home/pouwelse/venv/m2cdeps/lib/libcrypto.a build/temp.linux-x86_64-2.7/SWIG/_m2crypto_wrap.o -L/usr/lib64
    # -L/home/pouwelse/venv/m2cdeps/lib -Wl,-R/home/pouwelse/venv/m2cdeps/lib -lpython2.7 -o
    # build/lib.linux-x86_64-2.7/M2Crypto/__m2crypto.so

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
    # ./bjam -j$CONCURRENCY_LEVEL threading=multi -no_single -no_static --without-mpi --prefix=$VENV install
    popd
    touch $BOOST_MARKER
fi



#
# Build Libtorrent and its python bindings
#
pushd $VENV/src
LIBTORRENT_VERSION=1.1.0
LIBTORRENT_MARKER=`build_marker libtorrent $LIBTORRENT_VERSION`
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
    # mkdir -p $VENV/lib/python2.7/site-packages/
    cp $VENV/src/libtorrent-rasterbar-$LIBTORRENT_VERSION/bindings/python/bin/*/*/libtorrent-python-*/*/libtorrent.so $VENV/lib/python2.7/site-packages/
    popd
    popd
    # Check that the modules work
    python -c "import libtorrent"
    touch $LIBTORRENT_MARKER
fi

# We don't use it anymore
# # wxpython
# pushd $VENV/src
# if [ ! -e wxPython-*.tar.bz2 ]; then
#     wget http://garr.dl.sourceforge.net/project/wxpython/wxPython/2.8.12.1/wxPython-src-2.8.12.1.tar.bz2
# fi
# if [ ! -d wxPython*/ ]; then
#     tar xavf wxPython-*.tar.bz2
# fi
# pushd wxPython*/
# if [ ! -e $VENV/lib/libwx_gtk2u_gizmos_xrc-*.so ]; then
#     make uninstall ||:
#     make clean ||:
#     ./configure --prefix=$VENV \
#         --enable-display \
#         --enable-geometry \
#         --enable-graphics_ctx \
#         --enable-sound \
#         --enable-unicode \
#         --with-gtk \
#         --with-libjpeg=sys \
#         --with-libpng=sys \
#         --with-libtiff=builtin \
#         --with-sdl \
#         --with-zlib=sys \
#         --without-gnomeprint \
#         --without-opengl \
#         --with-expat=sys
#     # TODO(emilon): Are those CFLAGS needed?
#     CFLAGS="-Iinclude" make -j$CONCURRENCY_LEVEL || CFLAGS="-Iinclude" make
#     make install
#     pushd contrib
#     make -j$CONCURRENCY_LEVEL || make
#     make install
#     popd
# fi
# pwd

# if [ ! -e $VENV/lib/python*/site-packages/wx-*/wxPython/_wx.py ]; then
#     pushd wxPython
#     python setup.py build BUILD_GLCANVAS=0 #BUILD_STC=0
#     python setup.py install BUILD_GLCANVAS=0 #BUILD_STC=0
#     popd
# fi
# popd

# recent libgmp needed by pycrypto
GMP_VERSION=6.1.0
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
LIBSODIUM_VERSION=1.0.10
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

# remove pil as it doesn't work (pillow will be installed shortly)
rm -f $VENV/bin/pil*
rm -rf $VENV/lib/python2.7/site-packages/PIL

#pip install --upgrade pip

sed -i 's~#!/usr/bin/env python2.6~#!/usr/bin/env python2~' $VENV/bin/*
easy_install pip

# CFFI needs to be installed before pynacl or pip will find the older system version and faild to build it...
CFLAGS="$CFLAGS -I$VENV/include" LDFLAGS="$LDFLAGS -L$VENV/lib" pip install --upgrade cffi

echo "
Jinja2 # Used for systemtap report generation scripts from Cor-Paul
configobj
cryptography
cython
gmpy==1.16
ipython
nose
nosexcover
ntplib
pillow
psutil
pyasn1 # for twisted
pycparser
pycrypto # Twisted needs it
pynacl # New EC crypto stuff for tunnelcommunity
pysqlite
pyzmq
service_identity
six
twisted # Used by the config server/clients
unicodecsv # used for report generation scripts from Cor-Paul
validate
" > ~/requirements.txt

# For some reason the pip scripts get a python 2.6 shebang, fix it.
sed -i 's~#!/usr/bin/env python2.6~#!/usr/bin/env python2~' $VENV/bin/pip*

# numpy # used for report generation scripts from Cor-Paul, installed all by itself as it fails to build if we pass CFLAGS & co.
pip install numpy

# install netifaces separately because it requires some params now
pip install netifaces --allow-external netifaces --allow-unverified netifaces

CFLAGS="$CFLAGS -I$VENV/include" LDFLAGS="$LDFLAGS -L$VENV/lib" pip install --upgrade -r ~/requirements.txt

# meliae is not on the official repos
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
