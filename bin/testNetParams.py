import vtpalmetto
import pypalmetto
from sh import rm, Command, cp
import re
import argparse
import time
import numpy as np
import trainWithParams
from hyperopt import fmin, tpe, hp                                                                                                                                                                                              
from hyperopt.mongoexp import MongoTrials


runHours = 48
vtp = vtpalmetto.VTPalmetto()
vtp.qsubParams = dict(l='select=1:ncpus=1:mem=20gb:ngpus=1:gpu_model=k40,walltime={0}:00:00'.format(
    runHours))
vtp.name = 'testNetParams'

maxAtSameTime = 15

hostname = '130.127.249.119'
dbname = 'vdnet4_db'
trials = MongoTrials('mongo://'+hostname+':1234/'+dbname+'/jobs', exp_key='exp1')

def _print_line(line):
    print line.encode("utf-8")

def task(index):
    hmw = Command('hyperopt-mongo-worker')
    hmw('--mongo={0}:{1}/{2}'.format(hostname,1234,dbname), _out=_print_line, _err=_print_line)

    return 'done'
    



parser = argparse.ArgumentParser()
parser.add_argument('command', choices=['submit', 'status', 'results', 'master'])
args = parser.parse_args()


space = {
        'detectorSize': hp.quniform('detectorSize', 25, 75, 1), 
        'conv1N':hp.quniform('conv1N', 10, 25, 1.0), 
        'conv1Size':1+hp.quniform('conv1Size', 4, 6, 2), 
        'conv2N':hp.quniform('conv2N', 10, 25, 1), 
        'conv2Size':1+hp.quniform('conv2Size', 4, 6, 2), 
        'fc1N':hp.quniform('fc1N', 10, 25, 1)}


if args.command == 'master':
    best = fmin(trainWithParams.task, space, trials=trials, algo=tpe.suggest, max_evals=50)
    print best

elif args.command == 'submit':
    palmetto = pypalmetto.Palmetto()
    for i in range(maxAtSameTime):
        j = palmetto.createJob(task, dict(index=i), vtp.name, 
                vtp.qsubParams)
        s = j.getStatus()
        if s == pypalmetto.JobStatus.NotSubmitted or s == pypalmetto.JobStatus.Completed:
            print "submitting with index == {0}".format(i)
            j.submit(force=True)
        else:
            print "not submitting with index == {0}, status={1}".format(i,s)


elif args.command == 'status':
    vtpalmetto.printStatus(vtp)
elif args.command == 'results':
    #print trials.statuses()
    #print trials.losses()
    #print trials.results
    #print trials.trials
    from tabulate import tabulate
    #import copy
    res = []
    for t in trials.trials:
        r = t['result']
        if r['status'] == 'ok':
            #d = copy.copy(t['misc']['vals']) 
            d = dict([(k, int(v[0])) for k,v in t['misc']['vals'].iteritems() ])
            d['loss'] = r['loss']
            res.append(d)
            #print t['misc']['vals'].values()
            #print t['vals']
    print "There are {0} finished results! ({1} total, {2} new)".format(
            len(res), len(trials.trials),
            sum(s == 'new' for s in trials.statuses()))

    print tabulate(sorted(res, key=lambda x:x['loss']), headers='keys')
    
