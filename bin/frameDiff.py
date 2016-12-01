import vtpalmetto
from sh import rm, Command, cp
import re
import argparse
import time
import numpy as np


runHours = 10
vtp = vtpalmetto.VTPalmetto()
vtp.qsubParams = dict(l='select=1:ncpus=2:mem=16gb,walltime={0}:00:00'.format(
    runHours))
vtp.name = 'frameDiff'

testFrames = [10, 11, 12, 13, 14]
trainFrames = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]

x=0
y=0
w=5300
h=3500
sz=300
n=20

def task(dataset, _job):
    startTime = time.time()
    vtp.setJob(_job)

    vtp.gotoTmp()
    rm('-rf', 'vehicleTracking')
    vtp.getVT()
    vtp.cmakeVT()

    vtp.makeVT('basicDetector')
    basicDetector = Command("util/basicDetector")
    vtp.makeVT('detectionAccuracy')
    detectionAccuracy = Command("util/detectionAccuracy")

    cp('-r', vtp.srcDir+'/data/labels/skycomp1', '.')

    results = dict()


    for threshold in np.arange(5, 251, 5):
        basicDetector('-r', x, y, w, h, '-s', sz, '-n', n, '-g', vtp.gpuDev, '-t', threshold, "-d", "diff", dataset)

        out = detectionAccuracy(l=dataset, d='detections.pb', 
                t=' '.join(str(t) for t in trainFrames),
                T=' '.join(str(t) for t in testFrames))
        mode = ['TRAIN', 'TEST']
        value = ['TP', 'FP', 'DP', 'FN']
        pattern = ''.join('{0} {1}:\s+(?P<{0}_{1}>\d+).*'.format(m,v) for m in mode for v in value)
        match = re.search(pattern, out.stdout, re.DOTALL)
        if match:
            results[threshold] = match.groupdict()
        else:
            results[threshold] = out.stdout
            print 'ERROR, could not find pattern in "{0}"'.format(out.stdout)
    def missRate(r):
        tp = float(r['TEST_TP'])
        fn = float(r['TEST_FN'])
        #print "tp={0},fn={1}, mr={2}".format(tp,fn,  fn/(fn+tp))
        return fn/(fn+tp)
    def FPPI(r, n):
        fp = float(r['TEST_FP']) + float(r['TEST_DP'])
        return fp/n

    return dict(
            results = results, 
            MRvFPPI = [(
                FPPI(r, len(testFrames)), 
                missRate(r), 
                t)  for t, r in results.iteritems()
            ])


parser = argparse.ArgumentParser()
parser.add_argument('command', choices=['submit', 'status', 'results'])
args = parser.parse_args()

if args.command == 'submit':
    vtpalmetto.submit(vtp,task,[dict(dataset='skycomp1')])
elif args.command == 'status':
    vtpalmetto.printStatus(vtp)
elif args.command == 'results':
    jobs =vtp.getJobs()
    for j in jobs:
        ret=j.decode(j.retVal)
        #d = {}
        #for k in ret[0].keys():
            #d[k] = [int(ret[i][k]) for i in sorted(ret.keys())]
        #print d
        print ret

