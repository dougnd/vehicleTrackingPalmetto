import socket
import os
from sh import git, cp, rm, cmake, make, mkdir, Command
import argparse
import pypalmetto


class VTPalmetto(object):
    def __init__(self):
        hostname = socket.gethostname()
        self.isPalmetto = hostname == 'user001'
        if self.isPalmetto:
            self.srcDir = '/scratch2/dndawso/vehicleTracking'
            self.installDir = os.environ['HOME'] + '/usr/local'
            self.cmakeParams = [
                    '-DDATA_DIR=/scratch2/dndawso/vehicleTracking/data',
                    '-DCAFFE_DIR='+self.installDir,
                    '-DBOOST_ROOT='+self.installDir,
                    '-DBoost_NO_BOOST_CMAKE=ON',
                    '-DLEVELDB_ROOT='+self.installDir,
                    '-DUSE_MKL=ON',
                    '-DCMAKE_PREFIX_PATH='+self.installDir,
                    '-DJAVA_CACHE_DIR=/scratch2/dndawso/javaCache'
                    ]
        else:
            self.srcDir = '/home/doug/Documents/research/vehicleTracking'
            self.cmakeParams = [
                    '-DDATA_DIR='+self.srcDir+'/data',
                    '-DJAVA_CACHE_DIR=/home/doug/Documents/research/vehicleTracking/build/javaTracker'
                    ]

        self.name = 'unnamed'

        self.qsubParams = dict(l='select=1:ncpus=1:mem=1gb,walltime=0:30:00')

        self.palmetto = pypalmetto.Palmetto()

    def getTmpDir(self):
        if self.isPalmetto:
            return os.environ['TMPDIR']
        else:
            return '/tmp'

    def gotoTmp(self):
        os.chdir(self.getTmpDir())

    def getVT(self):
        git('clone', '-s', self.srcDir)
        os.chdir('vehicleTracking')
        git('pull')
        rm('-rf', 'build')
        mkdir('build')
        os.chdir('build')

    def cmakeVT(self):
        cmake(*self.cmakeParams + ['..'])

    def makeVT(self, *args):
        make(*args)


    def submit(self, task,params):
        for p in params:
            j = self.palmetto.createJob(task, p, self.name, self.qsubParams)
            print len(j.runFunc)
            if self.isPalmetto:
                j.submit()
            else:
                j.executeLocal()

    def getJobs(self):
        return self.palmetto.getJobsWithName(self.name)

    def getJobByParams(self, **kwarg):
        if '_jobs' in kwarg:
            jobs = kwarg['_jobs']
            del kwarg['_jobs']
        else:
            jobs = self.getJobs()

        for j in jobs:
            params = j.decode(j.params)
            if all(item in params.items() for item in kwarg.items()):
                return j

        return None


    def printStatus(self):
        jobs = self.getJobs()
        self.palmetto.updateDBJobStatuses()

        numR = len([0 for j in jobs if j.getStatus(True) == pypalmetto.JobStatus.Running])
        numQ = len([0 for j in jobs if j.getStatus(True) == pypalmetto.JobStatus.Queued])
        numC = len([0 for j in jobs if j.getStatus(True) == pypalmetto.JobStatus.Completed])
        numE = len([0 for j in jobs if j.getStatus(True) == pypalmetto.JobStatus.Error])

        print "job status:"
        print('R: {0}, Q: {1}, C: {2}, E: {3}'.format(numR, numQ, numC, numE))

    def main(self, task, params):
        parser = argparse.ArgumentParser(prog=self.name)
        parser.add_argument('command', choices=['submit', 'status'])

        args = parser.parse_args()

        if args.command == 'submit':
            submit(task,params)
        if args.command == 'status':
            printStatus()




