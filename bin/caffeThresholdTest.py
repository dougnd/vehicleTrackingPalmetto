import vtpalmetto
from sh import rm, Command, cp, mkdir
import re
import argparse
import time
import numpy as np

runHours = 10
vtp = vtpalmetto.VTPalmetto()
vtp.qsubParams = dict(l='select=1:ncpus=1:mem=16gb:ngpus=1:gpu_model=k40,walltime={0}:00:00'.format(
    runHours))
vtp.name = 'caffeThresoldTest'

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

def task(dataset, modelLocation, frameDiff, detectorSize, netParams,  _job):
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

    vtp.makeVT('basicDetector')
    basicDetector = Command("util/basicDetector")
    vtp.makeVT('detectionAccuracy')
    detectionAccuracy = Command("util/detectionAccuracy")

    cp('-r', vtp.srcDir+'/data/labels/skycomp1', '.')
    cp(vtp.srcDir+'/../negatives.yml', '.')

    mkdir('-p', 'src/caffe')
    cp('{0}/vehicle_detector_train_iter_{1}.caffemodel'.format(modelLocation, caffeIterations), 'src/caffe/')
    cp('{0}/mean.cvs'.format(modelLocation), 'src/caffe/')


    vtp.makeVT('buildNet')

    results = dict()
    for threshold in np.arange(-2.0, 4.0, 0.2):
        print "running with threshold = {0}".format(threshold)
        bdArgs = ['-r', x, y, w, h, '-s', sz, '-n', n, '-g', vtp.gpuDev, '-t', threshold, dataset ]
        if frameDiff != 0:
            bdArgs.append('-f')
            bdArgs.append(frameDiff)
        vtp.basicDetector(*bdArgs)

        out = vtp.detectionAccuracy(l=dataset, d='detections.pb', 
                t=' '.join(str(t) for t in trainFrames),
                T=' '.join(str(t) for t in testFrames))
        results[threshold] = out

    return results
    


parser = argparse.ArgumentParser()
parser.add_argument('command', choices=['submit', 'status', 'results'])
class optionalFile(argparse.FileType):
    def __call__(self, string):
        if string == None:
            return None
        return super(optionalFile,self).__call__(string)

parser.add_argument('-f', '--filename', default=None, type=optionalFile('w'))
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
        dataset='skycomp1',
        modelLocation='/home/dndawso/vtp-results/doTrainDetect/vzrOnuSk+pafKXN3K7M1lg==',
        detectorSize=60,
        netParams=netParams,
        frameDiff=1) ])
elif args.command == 'status':
    vtpalmetto.printStatus(vtp)
elif args.command == 'results':
    jobs =vtp.getJobs()
    from tabulate import tabulate
    for j in jobs:
        ret=j.decode(j.retVal)
        params=j.decode(j.params)
        print 'params: {0}'.format(params)
        ret = sorted((dict(threshold=k, **v) for k,v in ret.iteritems()), key=lambda x:x['threshold'])

        print tabulate(ret, headers='keys')
        if args.filename != None:
            import json
            print "writing out results to file"
            args.filename.write(json.dumps(ret))
    
