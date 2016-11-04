import vtpalmetto
from sh import rm, Command
from itertools import product
import argparse
import pypalmetto 

vtp = vtpalmetto.VTPalmetto()
vtp.qsubParams = dict(l='select=1:ncpus=2:mem=10gb,walltime=6:00:00')

def doSim(err, fileName, weights):

    vtp.gotoTmp()
    rm('-rf', 'vehicleTracking')
    vtp.getVT()
    vtp.cmakeVT()
    vtp.makeVT('tracker')
    tracker = Command("javaTracker/runTracker.sh")
    ret={}
    for w in weights:
        rm('-rf', 'output.csv')
        for line in tracker(f=fileName, p=err, n=err, g=False, a=5, w=w, _iter=True):
            print(line)
        
        with open('output.csv', 'r') as f:
            out = f.read().split(',')
            out = [o.strip() for o in out]
            print out
            ret[w]=out
    return ret



parser = argparse.ArgumentParser()
parser.add_argument('command', choices=['submit', 'status', 'results'])
parser.add_argument('-a', '--appearance', action='store_true')

args = parser.parse_args()

senarios = ['1lane_divided', '1lane_undivided', '2lane_divided', '2lane_undivided']
freq = [1, 5, 10]
errorList = [0.0, 0.05, 0.1]
def fname(s,f):
    return '{0}/data/vehicleSimulation/{1}_{2}hz.csv'.format(vtp.srcDir, s, f)


params = []
if args.appearance:
    vtp.name = 'simTrackApp'
    weights = [0.0, 0.1, 0.5, 1.0, 2.0, 10.0]
    fnames = [fname(senarios[0],f) for f in freq]
    params = list(dict(zip(['err', 'fileName'], x)) for x in 
        product(errorList, fnames))
    for p in params:
        p['weights'] = weights

else:
    vtp.name = 'simTrack'
    fnames = [fname(s,f) for (s,f) in product(senarios, freq)]
    params = list(dict(zip(['err', 'fileName'], x)) for x in 
        product(errorList, fnames))
    for p in params:
        p['weights'] = [0]


if args.command == 'submit':
    vtpalmetto.submit(vtp,doSim,params)
elif args.command == 'status':
    vtpalmetto.printStatus(vtp)
elif args.command == 'results':
    jobs = vtp.getJobs()
    if not args.appearance:
        tables = {}
        for s in senarios:
            tables[s] = []
            for f in freq:
                for err in errorList:
                    j = vtp.getJobByParams(_jobs=jobs, err=err, 
                            fileName=fname(s,f))
                    if j.getStatus(True) == pypalmetto.JobStatus.Completed:
                        #print j.decode(j.retVal)
                        r = j.decode(j.retVal)[0.0]
                        #print r
                        tables[s].append([
                            f, err*100,float(r[5]), float(r[4]), 
                            float(r[3]), float(r[6])/float(r[4])*100.0, 
                            float(r[7])/float(r[4])*100, 
                            float(r[8])/float(r[4])*100.0, float(r[10]), 
                            float(r[11])])
            with open(s+'_out.csv', 'w') as fo:
                for l in tables[s]:
                    fo.write(','.join([str(i) for i in l]))
                    fo.write('\n')
    else:
        s= '1lane_divided'
        table = []
        table.append(['', 'error:'] + [0.0]*5 +[0.05]*5+[0.1]*5)
        table.append(['freq', 'weight'] + ['NVT', 'NMT', 'NFT', 'ANST', 'ATC']*3)
        for f in [1, 5, 10]:
            for w in weights:
                line = [f, w]
                for err in errorList:
                    j = vtp.getJobByParams(_jobs=jobs, err=err, 
                            fileName=fname(s,f))
                    if j.getStatus(True) != pypalmetto.JobStatus.Completed:
                        continue

                    r = j.decode(j.retVal)[w]
                    print r
                    line.extend([
                         float(r[6])/float(r[4])*100.0, 
                        float(r[7])/float(r[4])*100, 
                        float(r[8])/float(r[4])*100.0, float(r[10]), float(r[11])])
                table.append(line)
        with open(s+'_appearance_out.csv', 'w') as fo:
            for l in table:
                fo.write(','.join([str(i) for i in l]))
                fo.write('\n')


