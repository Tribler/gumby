#!/bin/bash
# dummy_logging_test.sh ---
#
# Filename: dummy_logging_test.sh
# Description:
# Author: Elric Milon
# Maintainer:
# Created: Thu Nov 14 17:03:18 2013 (+0100)

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

sleep 1

HOST=$(hostname)
echo "$HOST: stout/err test"
echo "$HOST: This goes to STDOUT" >&1
echo "$HOST: This goes to STDERR" >&2

#
# dummy_logging_test.sh ends here
