import vtpalmetto
from sh import rm, Command, cp
import re
import time
import numpy as np

testFrames = [10, 11, 12, 13, 14]
trainFrames = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
x=0
y=0
w=5300
h=3500
sz=100
n=16
caffeIterations = 4000
trainIter = 2


def task(args):
    for k in args.keys():
        args[k] = int(args[k])
    print args
    detectorSize = args['detectorSize']
    del args['detectorSize']
    dataset = 'skycomp1'
    vtp = vtpalmetto.VTPalmetto()
    startTime = time.time()
    vtp.gotoTmp()
    rm('-rf', 'vehicleTracking')
    vtp.getVT()
    vtp.cmakeParams.append('-DTRAIN_ITERATIONS='+str(caffeIterations))
    vtp.cmakeParams.append('-DDETECTOR_WIDTH='+str(detectorSize))
    vtp.cmakeParams.append('-DDETECTOR_HEIGHT='+str(detectorSize))
    vtp.changeNetParams(**args)
    vtp.cmakeVT()

    vtp.makeVT('labeledDataToDB')
    labeledDataToDB = Command("util/labeledDataToDB")
    vtp.makeVT('basicDetector')
    basicDetector = Command("util/basicDetector")
    vtp.makeVT('detectionAccuracy')
    detectionAccuracy = Command("util/detectionAccuracy")

    cp('-r', vtp.srcDir+'/data/labels/skycomp1', '.')

    results = []
    #i = -1
    for i in range(trainIter):
    #while time.time() < (startTime + 60*60*runHours):
        #i+=1
        rm('-rf', 'src/caffe/train.leveldb', 'src/caffe/test.leveldb')
        labeledDataParams = dict(l=dataset, n='negatives.yml', 
                t=' '.join(str(t) for t in trainFrames),
                T=' '.join(str(t) for t in testFrames))
        if i != 0: 
            labeledDataParams['d']='detections.pb'

        labeledDataToDB(**labeledDataParams)
        vtp.makeVT('trainNet')
        vtp.makeVT('buildNet')
        basicDetector('-r', x, y, w, h, '-s', sz, '-n', n, '-g', vtp.gpuDev, dataset)

        out = detectionAccuracy(l=dataset, d='detections.pb', 
                t=' '.join(str(t) for t in trainFrames),
                T=' '.join(str(t) for t in testFrames))
        mode = ['TRAIN', 'TEST']
        value = ['TP', 'FP', 'DP', 'FN']
        pattern = ''.join('{0} {1}:\s+(?P<{0}_{1}>\d+).*'.format(m,v) for m in mode for v in value)
        match = re.search(pattern, out.stdout, re.DOTALL)
        if match:
            res = match.groupdict()
            tp = float(res['TEST_TP'])
            fn = float(res['TEST_FN'])
            dp = float(res['TEST_DP'])
            fp = dp + float(res['TEST_FP'])
            p = tp/(tp+fp)
            r = tp/(tp+fn)
            res['TEST_P'] = p
            res['TEST_R'] = r
            res['TEST_F2'] = 5.0*p*r/(4*p+r)
            print "done with iter {0}".format(i)
            print res  
            results.append(res)
        else:
            print "error, no match!"
            print "STDOUT: ", out.stdout
            return dict(loss = 1e6, status='fail', status_fail='error could not find match ')

    print results
    max_f2 = max([r['TEST_F2'] for r in results])

    ret = dict(
            loss=-max_f2,
            status='ok',
            rawResults=results)
    print ret
    return ret


