#!/usr/bin/env python
import sys
import os
from sys import argv, exit

# parses the stderr output of each libswift client
def parse_stderr(logDir, outputDir, clientName):

    logfile = os.path.join(logDir, '00000.err')
    datafile = os.path.join(outputDir, clientName + '.err')
    if not os.path.exists( logfile ) or not os.path.isfile( logfile ):
        print >> sys.stderr, "Either the input or the output file is missing"
        exit(1)
    if os.path.exists( datafile ):
        print >> sys.stderr, "Output already present"
        exit(1)
        
    fl = None
    fd = None
    try:
        fl = open( logfile, 'r' )
        fd = open( datafile, 'w' )
        fd.write( "time percent upspeed dlspeed\n0 0 0 0\n" )
        relTime = 0
        up_bytes = 0
        down_bytes = 0
        for line in fl:
            if line[:5] == 'SLEEP':
                relTime += 1
            elif line[:4] == 'done' or line[:4] == 'DONE':
                # Split over ' ', then over ',', then over '(', then over ')', and keep it all in one array
                split = reduce( lambda x,y: x + y.split( ')' ), reduce(lambda x,y: x + y.split( '(' ), reduce(lambda x,y: x + y.split( ',' ), line.split( ' ' ), []), []), [])
                dlspeed = (int(split[16]) - down_bytes) / 1024.0
                down_bytes = int(split[16])
                upspeed = (int(split[10]) - up_bytes) / 1024.0
                up_bytes = int(split[10])
                                    
                percent = 0
                if int(split[3]) > 0:
                    percent = 100.0 * ( float(int(split[1])) / float(int(split[3])) )
                    
                fd.write( "{0} {1} {2} {3}\n".format( relTime, percent, upspeed, dlspeed ) )
                relTime += 1
    finally:
        try:
            if fd:
                fd.close()
        except Exception:
            pass
        try:
            if fl:
                fl.close()
        except Exception:
            pass

def check_single_experiment(inputDir, outputDir):
    #seeder
    if os.path.exists( os.path.join(inputDir, 'src') ):
        parse_stderr( os.path.join(inputDir, 'src'), outputDir, "seeder" )
    else:
        print >> sys.stderr, "Missing seeder stderr log!!"

# checks the current dir structure 
def check_dir(inputDir, outputDir):
    # check for single execution
    if os.path.exists( os.path.join(inputDir, 'output/src') ):
        #seeder
        check_single_experiment( os.path.join(inputDir, 'output'), outputDir)

    # TODO multiple experiments
    else:
        print >> sys.stderr, "Multiple experiments"
        pass


if __name__ == "__main__":
    if len(argv) < 3:
        print >> sys.stderr, "Usage: %s <input-directory> <output-directory>" % (argv[0])
        print >> sys.stderr, "Got:", argv

        exit(1)

    check_dir(argv[1], argv[2])
