import vtpalmetto
from sh import rm, Command, cp
import re
import argparse
import time
import numpy as np


runHours = 1
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
    vtpalmetto.submit(vtp,task,[dict(dataset='skycomp1')])
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
        #d = {}
        #for k in ret[0].keys():
            #d[k] = [int(ret[i][k]) for i in sorted(ret.keys())]
        #print d


