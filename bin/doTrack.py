import vtpalmetto
from sh import rm, Command, cp
import re
import argparse
import time
import numpy as np

runHours = 6
vtp = vtpalmetto.VTPalmetto()
vtp.qsubParams = dict(l='select=1:ncpus=1:mem=16gb:ngpus=1:gpu_model=k40,walltime={0}:00:00'.format(
    runHours))
vtp.name = 'doTrack'


def task(fileName, _job):
    startTime = time.time()
    vtp.setJob(_job)
    vtp.gotoTmp()
    rm('-rf', 'vehicleTracking')
    vtp.getVT()
    vtp.cmakeVT()

    vtp.makeVT('tracker')
    tracker = Command("javaTracker/runTracker.sh")

    rm('-rf', 'output.csv', 'frame_output.csv')
    for line in tracker(f=fileName, g=False, n=0.03, p=0.06, m=2.0, e=True, _iter=True):
        print(line)

    vtp.export('frame_output.csv')
    vtp.export('output.csv')
    return True
    


parser = argparse.ArgumentParser()
parser.add_argument('command', choices=['submit', 'status', 'results'])
args = parser.parse_args()

if args.command == 'submit':
    fnames = [
            '/home/dndawso/skycomp1_15f.csv', 
            '/home/dndawso/skycomp1_27f.csv']
            #'/home/dndawso/skycomp1_100f.csv']
    vtpalmetto.submit(vtp,task,[dict(fileName=f) for f in fnames])
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
    
