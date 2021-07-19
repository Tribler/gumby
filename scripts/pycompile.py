#!/usr/bin/env python3
import re
from compileall import compile_dir
from sys import argv

compile_dir(argv[1], rx=re.compile('/[.]svn'), force=False, quiet=True)
