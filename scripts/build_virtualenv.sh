#/bin/bash
# setup_env.sh ---
#
# Filename: setup_env.sh
# Description:
# Author: Elric Milon
# Maintainer:
# Created: Wed May 22 19:18:49 2013 (+0200)

# Commentary:
#
#
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

# Code:
set -ex

if [ ! -z "$VIRTUALENV_DIR" ]; then
    VENV=$VIRTUALENV_DIR
else
    VENV=$HOME/venv
fi

write_extra_vars()
{
    if [ -e $PROJECTROOT/experiment_vars.sh ]; then
        echo "export EXTRA_LD_LIBRARY_PATH=$VENV/lib" >> $PROJECTROOT/experiment_vars.sh
    fi
}

# Build the systemtap enabled python runtime and systemtap itself
# if dtrace is available, if not, just build python 2.7
if [ ! -e $VENV/inst/.completed ]; then
    mkdir -p $VENV/src
    pushd $VENV/src
    if [ -e /usr/bin/dtrace ]; then
        WITH_SYSTEMTAP=yes
        EXTRA_CONFIG_OPTS=--with-dtrace
    else
        EXTRA_CONFIG_OPTS=--without-dtrace
    fi

    if [ "$WITH_SYSTEMTAP" == yes ]; then

        if [ ! -d systemtap-*/ ]; then
            if [ ! -e systemtap-*.gz ]; then
                wget http://sourceware.org/systemtap/ftp/releases/systemtap-2.2.tar.gz
            fi
            tar xavf systemtap-*.gz
        fi
        cd systemtap-*/
        ./configure --prefix=$VENV/inst --with-dyninst=$VENV/inst/
        make -j$(grep process /proc/cpuinfo | wc -l)
        make install
    fi

    if [ ! -e $VENV/src/cpython-2011 ]; then
        hg clone http://hg.jcea.es/cpython-2011
    fi

    if [ ! -e $VENV/inst/bin/python ]; then
        pushd cpython-2011
        hg checkout dtrace-issue13405_2.7
        sudo apt-get install libncurses-dev systemtap-sdt-dev ||:
        ./configure $EXTRA_CONFIG_OPTS --prefix=$VENV/inst --enable-shared
        cp Modules/Setup.dist Modules/Setup
        make -j$(grep process /proc/cpuinfo | wc -l)
        make install
        popd
    fi
    touch $VENV/inst/.completed
    popd
fi

if [ -e $VENV/.completed ]; then
    echo "The virtualenv has been successfully built in a previous run of the script."
    echo "If you want to rebuild it or the script has been updated, either delete $VENV/.completed"
    echo "or the full $VENV dir and re-run the script."
    write_extra_vars

    exit 0
fi

export LD_LIBRARY_PATH=$VENV/inst/lib:$VENV/lib:$LD_LIBRARY_PATH

if [ ! -d $VENV/bin/python ]; then
    #virtualenv   --no-site-packages --clear $VENV
    virtualenv -p $VENV/inst/bin/python --no-site-packages --system-site-packages --clear $VENV
fi

mkdir -p $VENV/src

source $VENV/bin/activate


# Install apsw manually as it is not available trough pip.
if [ ! -e $VENV/lib64/python2.6/site-packages/apsw.so ]; then
    pushd $VENV/src
    if [ ! -e apsw-*zip ]; then
        wget https://apsw.googlecode.com/files/apsw-3.7.16.2-r1.zip
    fi
    if [ ! -d apsw*/src ]; then
        unzip apsw*.zip
    fi
    cd apsw*/
    python setup.py fetch --missing-checksum-ok --all build --enable-all-extensions install # test # running the tests makes it segfault...
    popd
fi

# M2Crypto needs OpenSSL with EC support, but RH/Fedora doesn't provide it.
# We install it in a different place so it will not end up in LD_LIBRARY_PATH
# affecting the system's ssh binary.
M2CDEPS=$VENV/m2cdeps
mkdir -p $M2CDEPS
if [ ! -e $M2CDEPS/lib/libcrypto.so ]; then
    pushd $VENV/src
    wget https://www.openssl.org/source/openssl-1.0.1e.tar.gz
    tar xvzpf openssl*tar.gz
    pushd openssl-*/

    ./config --prefix=$M2CDEPS threads zlib shared --openssldir=$M2CDEPS/share/openssl
    make -j2 || make #Fails when building in multithreaded mode
    #make
    make install
    # Proper names for M2Crypto
    ln -s $M2CDEPS/lib/libssl.so.1.0.0 $M2CDEPS/lib/libssl.so.10
    ln -s $M2CDEPS/lib/libcrypto.so.1.0.0 $M2CDEPS/lib/libcrypto.so.10
    echo "Done"
    popd
    popd
fi

if [ ! -e $VENV/lib/python*/site-packages/M2Crypto*.egg ]; then
    pushd $VENV/src
    wget http://pypi.python.org/packages/source/M/M2Crypto/M2Crypto-0.21.1.tar.gz
    tar xvapf M2Crypto-*.tar.gz
    pushd $VENV/src/M2Crypto-*/
    python setup.py build || : # Do not run this, it will break the proper stuff made by build_ext
    python setup.py build_py
    # This should use our custom libcrypto (explicit RPATH)
    python setup.py build_ext --openssl=$M2CDEPS --rpath=$M2CDEPS/lib
    python setup.py install
    popd
fi

echo "Testing if the EC stuff is working..."
python -c "from M2Crypto import EC; print dir(EC)"


#Not sure if we need this:
#pushd build-tmp
#wget http://download.zeromq.org/zeromq-3.2.3.tar.gz
#tar xvzpf zeromq*tar.gz
#cd zeromq*/
#./configure --prefix=$VIRTUAL_ENV
#make -j$(grep processor /proc/cpuinfo | wc -l)
#popd


# Build libboost
pushd $VENV/src
if [ ! -e $VENV/lib/libboost_wserialization.so ]; then
    wget http://netcologne.dl.sourceforge.net/project/boost/boost/1.53.0/boost_1_53_0.tar.bz2
    tar xavf boost_*.tar.bz2
    cd boost*/
    ./bootstrap.sh
    ./b2 -j$(grep process /proc/cpuinfo | wc -l) --prefix=$VENV install
fi
popd


# Before continuing fix a stupid symlink bug
#cd $VENV
#rm lib64
#ln -s lib lib64
#cd

# Build Libtorrent and its python bindings
pushd $VENV/src
if [ ! -e $VENV/lib64/python2.6/site-packages/libtorrent.so ]; then
    wget --no-check-certificate https://libtorrent.googlecode.com/files/libtorrent-rasterbar-0.16.10.tar.gz
    tar xavf libtorrent-rasterbar-*.tar.gz
    cd libtorrent-rasterbar*/
    ./configure --with-boost-python --with-boost=$VENV/include/boost --with-boost-libdir=$VENV/lib --with-boost-system=boost_system --prefix=$VENV --enable-python-binding
    make -j$(grep process /proc/cpuinfo | wc -l) || make
    make install
    cd $VENV/lib
    ln -s libboost_python.so libboost_python-py27.so.1.53.0
    cd ../..
fi

echo "
ipython
ntplib
gmpy==1.16
pyzmq
twisted
pysqlite
netifaces
" > ~/requeriments.txt
pip install -r ~/requeriments.txt
rm ~/requeriments.txt

deactivate

virtualenv --relocatable $VENV

#rm -fR venv
#mv $VENV $VENV/../venv
rm -fR build-tmp

write_extra_vars

touch $VENV/.completed

echo "Done, you can use this virtualenv with:
	source venv/bin/activate
And exit from it with:
	activate
Enjoy."

env

#
# setup_env.sh ends here
