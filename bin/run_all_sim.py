#!/usr/bin/env python

import glob
from sh import git, cd, cp, rm, cmake, make, mkdir, Command
try:
    from sh import module
except ImportError:
    def module(*args):
        pass
import os
import pypalmetto
import socket
from itertools import product


def doSim(fp, fn, fileName, tmpDir, initialSource):
    if tmpDir == None:
        tmpDir = os.environ['TMPDIR']

    os.chdir(tmpDir)
    rm('-rf', 'vehicleTracking')
    cp('-r', initialSource, '.')
    os.chdir('vehicleTracking')
    git('pull')
    rm('-rf', 'build')
    mkdir('build')
    os.chdir('build')
    module('add', 'java/1.7.0')
    cmake('-DJAVA_CACHE_DIR='+initialSource+'/build/javaTracker', '..')
    make('tracker')
    tracker = Command("javaTracker/runTracker.sh")
    for line in tracker(f=fileName, p=fp, n=fn, g=False, a=0, _iter=True):
        print(line)

    
    with open('output.csv', 'r') as f:
        out = f.read().split(' ,')
        print out
        return out
    

hostname = socket.gethostname()
print("Running on: {0}".format(hostname))
isPalmetto = hostname == 'user001'

if isPalmetto:
    tmpDir = None
    initialSource = "/scratch2/dndawso/vehicleTracking"
else:
    tmpDir = "/tmp/sim"
    initialSource = "/tmp/sim/init/vehicleTracking"

files = glob.glob(initialSource + '/data/vehicleSimulation/*.csv')
print("got {0} files!".format(len(files)))

p = pypalmetto.Palmetto()


errorList = [0.0, 0.05, 0.1]

for err, fileName in product(errorList, files):
    j = p.createJob(doSim, dict(fp=err, fn=err, fileName=fileName, tmpDir=tmpDir, initialSource=initialSource))

    if isPalmetto:
        j.submit()
    else:
        j.executeLocal()

