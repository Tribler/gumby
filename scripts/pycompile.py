#!/usr/bin/env python3
# pycompile.py ---
#
# Filename: pycompile.py
# Description:
# Author: Elric Milon
# Maintainer:
# Created: Tue Oct  8 14:14:35 2013 (+0200)

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

from compileall import compile_dir
import re
from sys import argv
compile_dir(argv[1], rx=re.compile('/[.]svn'), force=False, quiet=True)


#
# pycompile.py ends here
