#!/usr/bin/env python

import glob
from sh import git, cd, cp, rm, cmake, make, mkdir, Command
import os
import pypalmetto
import socket
from itertools import product


def doSim(err, fileName, tmpDir, initialSource, qsubL, weights):
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
    #module('add','java/1.7.0')
    #print(module('list'))
    cmake('-DJAVA_CACHE_DIR='+initialSource+'/build/javaTracker', '..')
    make('tracker')
    tracker = Command("javaTracker/runTracker.sh")

    ret={}
    for w in weights:
        rm('-rf', 'output.csv')
        for line in tracker(f=fileName, p=err, n=err, g=False, a=5, w=w, _iter=True):
            print(line)

        
        with open('output.csv', 'r') as f:
            out = f.read().split(' ,')
            print out
            ret[w]=out
    return ret
    

hostname = socket.gethostname()
print("Running on: {0}".format(hostname))
isPalmetto = hostname == 'user001'

if isPalmetto:
    tmpDir = None
    initialSource = "/scratch2/dndawso/vehicleTracking"
    qsubL = 'select=1:ncpus=2:mem=10gb,walltime=6:00:00'
else:
    tmpDir = "/tmp/sim"
    initialSource = "/tmp/sim/init/vehicleTracking"
    qsubL = ''


files = glob.glob(initialSource + '/data/vehicleSimulation/*.csv')
print("got {0} files!".format(len(files)))

p = pypalmetto.Palmetto()


errorList = [0.0, 0.05, 0.1]
weights = [0.0, 0.1, 0.5, 1.0, 2.0, 10.0]

for err, fileName in product(errorList, files):
    j = p.createJob(doSim, dict(err=err, fileName=fileName, tmpDir=tmpDir, initialSource=initialSource, weights=weights,qsubL=qsubL), 'vehicleSim2')

    if isPalmetto:
        j.submit()
    else:
        j.executeLocal()


