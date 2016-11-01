#!/usr/bin/env python

import argparse
import pypalmetto 
import glob
from sh import git, cd, cp, rm, cmake, make, mkdir, Command
import os
import pypalmetto
from itertools import product
import re


parser = argparse.ArgumentParser(prog='pypalmetto')
parser.add_argument('-a', '--appearance', action='store_true')
parser.add_argument('command', choices=['submit', 'status', 'results'])


args = parser.parse_args()

name = 'simTrack'

p = pypalmetto.Palmetto()

def doSim(err, fileName, tmpDir, initialSource, weights):
    #if tmpDir == None:
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


def getHz(fname):
    match = re.search('_([0-9]+)hz', fname)
    if match:
        return int(match.group(1))
    return 0

def getSenario(fname):
    match = re.search('([12]lane_.*divided)', fname)
    if match:
        return match.group(1)
    return ''

if args.command == 'results':
    expectedWLen = 6 if args.appearance else 1
    jobs = [j for j in p.getJobsWithName(name) if len(j.decode(j.params)['weights']) == expectedWLen]
    if not args.appearance:
        senarios = ['1lane_divided', '1lane_undivided', '2lane_divided', '2lane_undivided']
        tables = {}
        for s in senarios:
            tables[s] = []
            for f in [1, 5, 10]:
                for err in [0.0, 0.05, 0.1]:
                    j = next(j for j in jobs 
                            if getHz(j.decode(j.params)['fileName']) == f and
                                getSenario(j.decode(j.params)['fileName']) == s and
                                j.decode(j.params)['err'] == err)
                    print('for f={0}, and s={1}, got a job!'.format(f,s))
                    if j.getStatus(True) == pypalmetto.JobStatus.Completed:
                        #print j.decode(j.retVal)
                        r = j.decode(j.retVal)[0.0][0].split(',')
                        #print r
                        tables[s].append([
                            f, err*100,float(r[5]), float(r[4]), float(r[3]), float(r[6])/float(r[4])*100.0, 
                            float(r[7])/float(r[4])*100, 
                            float(r[8])/float(r[4])*100.0, float(r[10]), float(r[11])])
                        #print tables[s]
            with open(s+'_out.csv', 'w') as fo:
                for l in tables[s]:
                    fo.write(','.join([str(i) for i in l]))
                    fo.write('\n')

    else:
        s= '1lane_divided'
        weights = [0.0, 0.1, 0.5, 1.0, 2.0, 10.0]
        for f in [1, 5, 10]:
            for err in [0.0, 0.05, 0.1]:
                for w in weights:
                    pass









elif args.command == 'status':
    expectedWLen = 6 if args.appearance else 1
    jobs = [j for j in p.getJobsWithName(name) if len(j.decode(j.params)['weights']) == expectedWLen]
    p.updateDBJobStatuses()

    numR = len([0 for j in jobs if j.getStatus(True) == pypalmetto.JobStatus.Running])
    numQ = len([0 for j in jobs if j.getStatus(True) == pypalmetto.JobStatus.Queued])
    numC = len([0 for j in jobs if j.getStatus(True) == pypalmetto.JobStatus.Completed])
    numE = len([0 for j in jobs if j.getStatus(True) == pypalmetto.JobStatus.Error])

    print "job status:"
    print('R: {0}, Q: {1}, C: {2}, E: {3}'.format(numR, numQ, numC, numE))

    exit()
    for j in jobs:
        if j.getStatus() == pypalmetto.JobStatus.Completed:
            p = j.decode(j.params)
            r = j.decode(j.retVal)
            #print "{0} -> {1}".format(p,r)

elif args.command == 'submit':
    initialSource = "/scratch2/dndawso/vehicleTracking"
    errorList = [0.0, 0.05, 0.1]
    weights = []
    tmpDir = None

    files = []
    if args.appearance:
        files = glob.glob(initialSource + '/data/vehicleSimulation/1lane_divided*.csv')
        weights = [0.0, 0.1, 0.5, 1.0, 2.0, 10.0]

    else:
        files = glob.glob(initialSource + '/data/vehicleSimulation/*.csv')
        weights = [0.0]

    for err, fileName in product(errorList, files):
        j = p.createJob(doSim, dict(
            err=err, 
            fileName=fileName, 
            tmpDir=tmpDir, 
            initialSource=initialSource, 
            weights=weights), name, 
            dict(l='select=1:ncpus=2:mem=25gb,walltime=6:00:00'))
        print('submitting: {0}'.format(j))
        j.submit()





