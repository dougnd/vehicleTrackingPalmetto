import socket
import os
from sh import git, cp, rm, cmake, make, mkdir, Command
try:
    from sh import qstat
except:
    print "No qstat found..."
import argparse
import pypalmetto
import re

palmetto = pypalmetto.Palmetto()

def _print_line(line):
    print line.encode("utf-8")

class VTPalmetto(object):
    def __init__(self):
        hostname = socket.gethostname()
        self.isPalmetto = hostname == 'user001'
        self.isPalmettoNode = 'node' in hostname
        if self.isPalmetto or self.isPalmettoNode:
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
        self.runHash = None
        self.pbsId = None
        self.gpuDev = None
        if 'PBS_JOBID' in os.environ:
            self.setPbsId(os.environ['PBS_JOBID'])
        self.qsubParams = dict(l='select=1:ncpus=1:mem=1gb,walltime=0:30:00')
    def setPbsId(self, pbsId):
        self.pbsId = pbsId
        if self.pbsId != 0:
            out = qstat(f=self.pbsId)
            hostname = socket.gethostname()
            pattern = 'exec_vnode.*'+hostname+'\[([0-9]+)\]'
            match = re.search(pattern, out.stdout)
            if match:
                self.gpuDev = int(match.group(1))
                os.environ['gpuDev'] = str(self.gpuDev)
                print 'Setting GPU device to: {0}'.format(self.gpuDev)
            else:
                print 'No GPU device found.'


    def setJob(self, job):
        self.runHash = job['runHash']
        self.setPbsId(job['pbsId'])

    def getTmpDir(self):
        if self.isPalmetto or self.isPalmettoNode:
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
        cmake(*self.cmakeParams + ['..'], _out=_print_line, _err=_print_line)
        

    def makeVT(self, *args):
        make(*args, _out=_print_line, _err=_print_line)

    def detectionAccuracy(self, **kwargs):
        da = Command("util/detectionAccuracy")
        out = da(**kwargs)
        mode = ['TRAIN', 'TEST']
        value = ['TP', 'FP', 'DP', 'FN']
        pattern = ''.join('{0} {1}:\s+(?P<{0}_{1}>\d+).*'.format(m,v) for m in mode for v in value)
        match = re.search(pattern, out.stdout, re.DOTALL)
        d = match.groupdict()
        d = dict([(k, int(v)) for k,v in d.iteritems() ])
        tp = float(d['TEST_TP'])
        fn = float(d['TEST_FN'])
        dp = float(d['TEST_DP'])
        fp = dp + float(d['TEST_FP'])
        p = tp/(tp+fp)
        r = tp/(tp+fn)
        d['TEST_P'] = p
        d['TEST_R'] = r
        d['TEST_F2'] = 5.0*p*r/(4*p+r)
        d['TEST_MR'] = fn/(fn+tp)
        if 'T' in kwargs:
            n = len(kwargs['T'])
            d['TEST_FPPI'] = fp/float(n)
        return d


    def _exportDir(self):
        if self.runHash:
            return os.environ['HOME'] + '/vtp-results/' + self.name + '/' + self.runHash
        return os.environ['HOME'] + '/vtp-results/' + self.name

    def export(self, fname):
        mkdir('-p', self._exportDir())
        cp(fname, self._exportDir())


    def getJobs(self):
        return palmetto.getJobsWithName(self.name)
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

    # call from build dir
    def changeNetParams(self, **kwarg):
        netFileName = '../src/caffe/defaultDetectorNet.prototxt'
        if 'netFileName' in kwarg:
            netFileName = kwarg['netFileName']
            del kwarg['netFileName']
        argmap = {
                #name : (line#, line_name)
                'conv1N': (9, 'num_output'),
                'conv1Size': (10, 'kernel_size'),
                'conv2N': (41, 'num_output'),
                'conv2Size': (43, 'kernel_size'),
                'fc1N': (70, 'num_output')}
        with open(netFileName, 'r') as f:
            data = f.readlines()
        for key, value in kwarg.iteritems():
            if not key in argmap:
                print "ERROR: {0} not in {1}".format(key, argmap)
                print "all args: {0}".format(kwarg)
                continue
            pattern = r"("+argmap[key][1]+r":\s+)\d+"
            replacement = r"\g<1>"+str(int(value))
            line = data[argmap[key][0]-1]
            #print (pattern, replacement, line)
            result = re.sub(pattern, replacement, line)
            #print "result: ", result
            data[argmap[key][0]-1] = result

        with open(netFileName, 'w') as f:
            f.writelines( data )




def submit(vtp, task,params):
    for p in params:
        j = palmetto.createJob(task, p, vtp.name, vtp.qsubParams)
        print len(j.runFunc)
        if vtp.isPalmetto:
            j.submit()
        else:
            j.executeLocal()

def printStatus(vtp):
    jobs = vtp.getJobs()
    palmetto.updateDBJobStatuses()

    numR = len([0 for j in jobs if j.getStatus(True) == pypalmetto.JobStatus.Running])
    numQ = len([0 for j in jobs if j.getStatus(True) == pypalmetto.JobStatus.Queued])
    numC = len([0 for j in jobs if j.getStatus(True) == pypalmetto.JobStatus.Completed])
    numE = len([0 for j in jobs if j.getStatus(True) == pypalmetto.JobStatus.Error])

    print "job status:"
    print('R: {0}, Q: {1}, C: {2}, E: {3}'.format(numR, numQ, numC, numE))

def main(vtp, task, params):
    parser = argparse.ArgumentParser(prog=vtp.name)
    parser.add_argument('command', choices=['submit', 'status'])

    args = parser.parse_args()

    if args.command == 'submit':
        submit(task,params)
    if args.command == 'status':
        printStatus()




