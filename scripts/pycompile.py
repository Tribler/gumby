#!/usr/bin/env python3
from compileall import compile_dir
import re
from sys import argv

compile_dir(argv[1], rx=re.compile('/[.]svn'), force=False, quiet=True)
