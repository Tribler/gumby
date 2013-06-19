#/bin/bash
# setup_env.sh ---
#
# Filename: setup_env.sh
# Description:
# Author: Elric Milon
# Maintainer:
# Created: Wed May 22 19:18:49 2013 (+0200)
# Version:
# Last-Updated:
#           By:
#     Update #: 16
# URL:
# Doc URL:
# Keywords:
# Compatibility:
#
#

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

VENV=$PWD/venv_tmp

virtualenv --no-site-packages --clear $VENV

source $VENV/bin/activate


#hack for m2crypto to build properly in RH/fedora
rm  -fR build-tmp ; mkdir build-tmp
pushd build-tmp
wget https://www.openssl.org/source/openssl-1.0.1e.tar.gz
tar xvzpf openssl*tar.gz
pushd openssl-*/
ls
./config --prefix=$VENV threads zlib shared  --openssldir=$VENV/share/openssl
#make -j$(grep processor /proc/cpuinfo | wc -l) #Fails when building in multithreaded mode
make
make install
echo "Done"
popd
popd

pip install m2crypto ||: # This will fail
pushd $VENV/build/m2crypto
python setup.py build_py
python setup.py build_ext --openssl=$VENV
#python setup.py build # Do not run this, it will break the proper stuff made by build_ext
python setup.py install
popd


# Install apsw manually as it is not available trough pip.
pushd build-tmp
wget https://apsw.googlecode.com/files/apsw-3.7.16.2-r1.zip
unzip apsw*.zip
cd apsw*/
python setup.py fetch --missing-checksum-ok --all build --enable-all-extensions install # test # running the tests makes it segfault...

# TODO: Fix this mess properly
export LD_LIBRARY_PATH=$VENV/lib:$LD_LIBRARY_PATH
export LD_RUN_PATH=$VENV/lib:$LD_RUN_PATH
export LD_PRELOAD=$VENV/lib/libcrypto.so
echo "Testing if the EC stuff is working..."
python -c "from M2Crypto import EC; print dir(EC)"
popd

#Not sure if we need this:
#pushd build-tmp
#wget http://download.zeromq.org/zeromq-3.2.3.tar.gz
#tar xvzpf zeromq*tar.gz
#cd zeromq*/
#./configure --prefix=$VIRTUAL_ENV
#make -j$(grep processor /proc/cpuinfo | wc -l)
#popd

pip install -r requeriments.txt

deactivate

virtualenv --relocatable $VENV

unset LD_PRELOAD
rm -fR venv
mv $VENV $VENV/../venv
rm -fR build-tmp

echo "Done, you can use this virtualenv with: 
	source venv/bin/activate 
And exit from it with:
	activate
Enjoy."


#
# setup_env.sh ends here
