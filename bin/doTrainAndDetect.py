import vtpalmetto
from sh import rm, Command, cp
import re
import argparse
import time
import numpy as np

runHours = 5
runHoursDetect = 12
runHoursBuffer = 4
vtp = vtpalmetto.VTPalmetto()
vtp.qsubParams = dict(l='select=1:ncpus=1:mem=16gb:ngpus=1:gpu_model=k40,walltime={0}:00:00'.format(
    runHours+runHoursDetect +runHoursBuffer))
vtp.name = 'doTrainDetect'

testFrames = [10, 11, 12, 13, 14]
trainFrames = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
x=0
y=0
w=5300
h=3500
sz=300
n=20
caffeIterations = 5000
#trainIterations = 9

def task(dataset, number, frameDiff, detectorSize, netParams,  _job):
    for k in netParams.keys():
        netParams[k] = int(netParams[k])
    startTime = time.time()
    vtp.setJob(_job)
    vtp.gotoTmp()
    rm('-rf', 'vehicleTracking')
    vtp.getVT()
    vtp.cmakeParams.append('-DTRAIN_ITERATIONS='+str(caffeIterations))
    vtp.cmakeParams.append('-DDETECTOR_WIDTH='+str(detectorSize))
    vtp.cmakeParams.append('-DDETECTOR_HEIGHT='+str(detectorSize))
    vtp.changeNetParams(**netParams)
    vtp.cmakeVT()

    vtp.makeVT('labeledDataToDB')
    labeledDataToDB = Command("util/labeledDataToDB")
    vtp.makeVT('basicDetector')
    basicDetector = Command("util/basicDetector")
    vtp.makeVT('detectionAccuracy')
    detectionAccuracy = Command("util/detectionAccuracy")

    cp('-r', vtp.srcDir+'/data/labels/skycomp1', '.')
    cp(vtp.srcDir+'/../negatives.yml', '.')

    results = []
    i = -1
    #for i in range(trainIterations):
    while time.time() < (startTime + 60*60*runHours):
        i+=1
        rm('-rf', 'src/caffe/train.leveldb', 'src/caffe/test.leveldb')
        labeledDataParams = dict(l=dataset, n='negatives.yml', 
                t=' '.join(str(t) for t in trainFrames),
                T=' '.join(str(t) for t in testFrames))
        if frameDiff:
            labeledDataParams['f']=frameDiff
        if i != 0: 
            labeledDataParams['d']='detections.pb'

        labeledDataToDB(**labeledDataParams)
        vtp.makeVT('trainNet')
        vtp.makeVT('buildNet')
        bdArgs = ['-r', x, y, w, h, '-s', sz, '-n', n, '-g', vtp.gpuDev, dataset ]
        if frameDiff != 0:
            bdArgs.append('-f')
            bdArgs.append(frameDiff)
        vtp.basicDetector(*bdArgs)

        out = vtp.detectionAccuracy(l=dataset, d='detections.pb', 
                t=' '.join(str(t) for t in trainFrames),
                T=' '.join(str(t) for t in testFrames))
        results.append(out)

    bdArgs = ['-r', x, y, w, h, '-s', sz, '-n', number, '-g', vtp.gpuDev, dataset ]
    if frameDiff != 0:
        bdArgs.append('-f')
        bdArgs.append(frameDiff)
    vtp.basicDetector(*bdArgs)
    vtp.export('detections.pb')
    vtp.export('src/caffe/mean.cvs')
    vtp.export('src/caffe/vehicle_detector_train_iter_'+str(caffeIterations)+'.caffemodel')
    vtp.export('negatives.yml')
    return results
    


parser = argparse.ArgumentParser()
parser.add_argument('command', choices=['submit', 'status', 'results'])
args = parser.parse_args()

if args.command == 'submit':
    netParams = dict(
            fc1N=108,
            conv1N=31,
            conv2N=58,
            conv1Size=5,
            conv2Size=7
            )

    vtpalmetto.submit(vtp,task,[dict(
        dataset='skycomp1', number=n,
        detectorSize=60,
        netParams=netParams,
        frameDiff=1) for n in range(50, 51, 50)])
elif args.command == 'status':
    vtpalmetto.printStatus(vtp)
elif args.command == 'results':
    jobs =vtp.getJobs()

    for j in jobs:
        if not j.retVal:
            continue
        ret=j.decode(j.retVal)
        params=j.decode(j.params)
        print params
    
