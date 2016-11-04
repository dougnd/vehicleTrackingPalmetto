import socket
import os
from sh import git, cp, rm, cmake, make, mkdir, Command
import argparse
import pypalmetto



hostname = socket.gethostname()
isPalmetto = hostname == 'user001'
if isPalmetto:
    tmpDir = os.environ['TMPDIR']
    srcDir = '/scratch2/dndawso/vehicleTracking'
    javaCache = '/scratch2/dndawso/javaCache'
    installDir = os.environ['HOME'] + '/usr/local'
    cmakeParams = [
            '-DDATA_DIR=/scratch2/dndawso/vehicleTracking/data',
            '-DCAFFE_DIR='+installDir,
            '-DBOOST_ROOT='+installDir,
            '-DBoost_NO_BOOST_CMAKE=ON',
            '-DLEVELDB_ROOT='+installDir,
            '-DUSE_MKL=ON',
            '-DCMAKE_PREFIX_PATH='+installDir,
            '-DJAVA_CACHE_DIR=/scratch2/dndawso/javaCache'
            ]
else:
    tmpDir = '/tmp'
    srcDir = '/home/doug/Documents/research/vehicleTracking'
    cmakeParams = [
            '-DDATA_DIR='+srcDir+'/data',
            '-DJAVA_CACHE_DIR=/home/doug/Documents/research/vehicleTracking/build/javaTracker'
            ]

name = 'unnamed'

qsubParams = dict(l='select=1:ncpus=1:mem=1gb,walltime=0:30:00')

palmetto = pypalmetto.Palmetto()

def gotoTmp():
    os.chdir(tmpDir)

def getVT():
    git('clone', '-s', srcDir)
    os.chdir('vehicleTracking')
    git('pull')
    rm('-rf', 'build')
    mkdir('build')
    os.chdir('build')

def cmakeVT():
    cmake(*cmakeParams + ['..'])

def makeVT(*args):
    make(*args)


def submit(task,params):
    for p in params:
        j = palmetto.createJob(task, p, name, qsubParams)
        print len(j.runFunc)
        if isPalmetto:
            j.submit()
        else:
            j.executeLocal()

def getJobs():
    return palmetto.getJobsWithName(name)

def getJobByParams(**kwarg):
    if '_jobs' in kwarg:
        jobs = kwarg['_jobs']
        del kwarg['_jobs']
    else:
        jobs = getJobs()

    for j in jobs:
        params = j.decode(j.params)
        if all(item in params.items() for item in kwarg.items()):
            return j

    return None


def printStatus():
    jobs = getJobs()
    palmetto.updateDBJobStatuses()

    numR = len([0 for j in jobs if j.getStatus(True) == pypalmetto.JobStatus.Running])
    numQ = len([0 for j in jobs if j.getStatus(True) == pypalmetto.JobStatus.Queued])
    numC = len([0 for j in jobs if j.getStatus(True) == pypalmetto.JobStatus.Completed])
    numE = len([0 for j in jobs if j.getStatus(True) == pypalmetto.JobStatus.Error])

    print "job status:"
    print('R: {0}, Q: {1}, C: {2}, E: {3}'.format(numR, numQ, numC, numE))

def main(task, params):
    parser = argparse.ArgumentParser(prog=name)
    parser.add_argument('command', choices=['submit', 'status'])

    args = parser.parse_args()

    if args.command == 'submit':
        submit(task,params)
    if args.command == 'status':
        printStatus()




