import vtpalmetto
from sh import rm, Command, cp
import re
import argparse
import time
import numpy as np

runHours = 10
runHoursBuffer = 4
vtp = vtpalmetto.VTPalmetto()
vtp.qsubParams = dict(l='select=1:ncpus=1:mem=16gb:ngpus=1:gpu_model=k40,walltime={0}:00:00'.format(
    runHours+runHoursBuffer))
vtp.name = 'testNetParams'

testFrames = [10, 11, 12, 13, 14]
trainFrames = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
x=0
y=0
w=5300
h=3500
sz=300
n=20
caffeIterations = 3000

def task(dataset, _job):
    startTime = time.time()
    vtp.setJob(_job)
    vtp.gotoTmp()
    rm('-rf', 'vehicleTracking')
    vtp.getVT()
    vtp.cmakeParams.append('-DTRAIN_ITERATIONS='+str(caffeIterations))
    vtp.cmakeVT()

    vtp.makeVT('labeledDataToDB')
    labeledDataToDB = Command("util/labeledDataToDB")
    vtp.makeVT('basicDetector')
    basicDetector = Command("util/basicDetector")
    vtp.makeVT('detectionAccuracy')
    detectionAccuracy = Command("util/detectionAccuracy")

    cp('-r', vtp.srcDir+'/data/labels/skycomp1', '.')

    i = -1
    #for i in range(trainIterations):
    while time.time() < (startTime + 60*60*runHours):
        i+=1
        rm('-rf', 'src/caffe/train.leveldb', 'src/caffe/test.leveldb')
        labeledDataParams = dict(l=dataset, n='negatives.yml', 
                t=' '.join(str(t) for t in trainFrames),
                T=' '.join(str(t) for t in testFrames))
        if i != 0: 
            labeledDataParams['d']='detections.pb'

        labeledDataToDB(**labeledDataParams)
        vtp.makeVT('trainNet')
        vtp.makeVT('buildNet')
        basicDetector('-r', x, y, w, h, '-s', sz, '-n', n, '-g', vtp.gpuDev,  dataset)

    out = detectionAccuracy(l=dataset, d='detections.pb', 
            t=' '.join(str(t) for t in trainFrames),
            T=' '.join(str(t) for t in testFrames))
    mode = ['TRAIN', 'TEST']
    value = ['TP', 'FP', 'DP', 'FN']
    pattern = ''.join('{0} {1}:\s+(?P<{0}_{1}>\d+).*'.format(m,v) for m in mode for v in value)
    match = re.search(pattern, out.stdout, re.DOTALL)
    results = match.groupdict()

    return results
    


parser = argparse.ArgumentParser()
parser.add_argument('command', choices=['submit', 'status', 'results'])
args = parser.parse_args()

if args.command == 'submit':
    vtpalmetto.submit(vtp,task,[dict(dataset='skycomp1', threshold=t) for t in np.arange(-1,3.0,0.5)])
elif args.command == 'status':
    vtpalmetto.printStatus(vtp)
elif args.command == 'results':
    jobs =vtp.getJobs()

    def missRate(r):
        tp = float(r['TEST_TP'])
        fn = float(r['TEST_FN'])
        #print "tp={0},fn={1}, mr={2}".format(tp,fn,  fn/(fn+tp))
        return fn/(fn+tp)
    def FPPI(r, n):
        fp = float(r['TEST_FP']) + float(r['TEST_DP'])
        return fp/n

    MRvFPPI = []
    for j in jobs:
        if not j.retVal:
            continue
        ret=j.decode(j.retVal)
        params=j.decode(j.params)
        d = {}
        for k in ret[0].keys():
            d[k] = [int(ret[i][k]) for i in sorted(ret.keys())]
        print d
        #print ret
        if 'threshold' in params.keys():
            best = ret[max(ret.keys())]
            MRvFPPI.append((
                    FPPI(best, len(testFrames)), 
                    missRate(best), 
                    params['threshold'])) 

    print MRvFPPI
    
