#!/usr/bin/env python

import glob
from sh import git, cd, cp, rm, module, cmake, make, mkdir
import os

def doSim(fp, fn, file, tmpDir, initialSource):
    if tmpDir == None:
        tmpDir = os.environ['TMPDIR']

    cp('-r', initialSource, '.')
    cd('vehicleTracking')
    git('pull')
    mkdir('-p', 'build')
    cd('build')
    module('add', 'java/1.7.0')
    cmake('..')
    make('tracker')
    

