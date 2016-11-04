import vtpalmetto
from sh import rm, Command, cp
import argparse

vtp = vtpalmetto.VTPalmetto()
vtp.qsubParams = dict(l='select=1:ncpus=1:mem=16gb:ngpus=1:gpu_model=k40,walltime=20:00:00')
vtp.name = 'repeatTrain'

testFrames = [10, 11, 12, 13, 14]
trainFrames = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
x=0
y=0
w=5300
h=3500
sz=300
n=20

def task(dataset):
    vtp.gotoTmp()
    rm('-rf', 'vehicleTracking')
    vtp.getVT()
    vtp.cmakeVT()

    vtp.makeVT('labeledDataToDB')
    labeledDataToDB = Command("util/labeledDataToDB")
    cp('-r', vtp.srcDir+'/data/labels/skycomp1', '.')

    labeledDataToDB(l=dataset, n='negatives.yml', 
            t=' '.join(str(t) for t in trainFrames),
            T=' '.join(str(t) for t in testFrames))
    vtp.makeVT('trainNet')
    vtp.makeVT('basicDetector')
    basicDetector = Command("util/basicDetector")
    vtp.makeVT('buildNet')
    basicDetector('-r', x, y, w, h, '-s', sz, '-n', n, dataset)

    vtp.makeVT('detectionAccuracy')
    detectionAccuracy = Command("util/detectionAccuracy")
    out = detectionAccuracy(l=dataset, d='detections.pb', 
            t=' '.join(str(t) for t in trainFrames),
            T=' '.join(str(t) for t in testFrames))
    return out
    


parser = argparse.ArgumentParser()
parser.add_argument('command', choices=['submit', 'status', 'results'])
args = parser.parse_args()

if args.command == 'submit':
    vtpalmetto.submit(vtp,task,[dict(dataset='skycomp1')])
elif args.command == 'status':
    vtpalmetto.printStatus(vtp)

