import vtpalmetto
from sh import rm, Command, cp
import re
import argparse
import time
import numpy as np

runHours = 12
runHoursBuffer = 4
vtp = vtpalmetto.VTPalmetto()
vtp.qsubParams = dict(l='select=1:ncpus=1:mem=16gb:ngpus=1:gpu_model=k40,walltime={0}:00:00'.format(
    runHours+runHoursBuffer))
vtp.name = 'repeatTrain2'

testFrames = [10, 11, 12, 13, 14]
trainFrames = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
x=0
y=0
w=5300
h=3500
sz=300
n=20
caffeIterations = 4000
#trainIterations = 9

def task(dataset, threshold, frameDiff, _job):
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
    #basicDetector = Command("util/basicDetector")
    vtp.makeVT('detectionAccuracy')
    #detectionAccuracy = Command("util/detectionAccuracy")

    cp('-r', vtp.srcDir+'/data/labels/skycomp1', '.')

    results = []
    i = -1
    #for i in range(trainIterations):
    bestF2 = 0.0
    while time.time() < (startTime + 60*60*runHours):
        i+=1
        rm('-rf', 'src/caffe/train.leveldb', 'src/caffe/test.leveldb')
        labeledDataParams = dict(l=dataset, n='negatives.yml', 
                t=' '.join(str(t) for t in trainFrames),
                T=' '.join(str(t) for t in testFrames))
        if i != 0: 
            labeledDataParams['d']='detections.pb'
        if frameDiff:
            labeledDataParams['f']=frameDiff

        labeledDataToDB(**labeledDataParams)
        vtp.makeVT('trainNet')
        vtp.makeVT('buildNet')
        bdArgs = ['-r', x, y, w, h, '-s', sz, '-n', n, '-g', vtp.gpuDev, '-t', threshold, dataset ]
        if frameDiff != 0:
            bdArgs.append('-f')
            bdArgs.append(frameDiff)
        vtp.basicDetector(*bdArgs)

        out = vtp.detectionAccuracy(l=dataset, d='detections.pb', 
                t=' '.join(str(t) for t in trainFrames),
                T=' '.join(str(t) for t in testFrames))
        results.append(out)
        if out['TEST_F2'] > bestF2:
            bestF2 = out['TEST_F2']
            vtp.export('src/caffe/mean.cvs')
            vtp.export('src/caffe/vehicle_detector_train_iter_'+str(caffeIterations)+'.caffemodel')
            vtp.export('negatives.yml')

    return results
    


parser = argparse.ArgumentParser()
parser.add_argument('command', choices=['submit', 'status', 'results'])
args = parser.parse_args()

if args.command == 'submit':
    #vtpalmetto.submit(vtp,task,[dict(dataset='skycomp1', threshold=t) for t in np.arange(-1,3.0,0.5)])
    vtpalmetto.submit(vtp,task,[dict(dataset='skycomp1', threshold=0, frameDiff=fd) for fd in range(3)])
elif args.command == 'status':
    vtpalmetto.printStatus(vtp)
elif args.command == 'results':
    jobs =vtp.getJobs()

    from tabulate import tabulate
    for j in jobs:
        if not j.retVal:
            continue
        ret=j.decode(j.retVal)
        params=j.decode(j.params)
        print 'params: {0}'.format(params)
        print tabulate(ret, headers='keys')

    
