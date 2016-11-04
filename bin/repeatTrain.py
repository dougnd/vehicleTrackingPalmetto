import vtpalmetto
from sh import rm


def task(**kwarg):
    print 'hello world'
    vtpalmetto.gotoTmp()
    rm('-rf', 'vehicleTracking')
    vtpalmetto.getVT()
    vtpalmetto.cmakeVT()
    vtpalmetto.makeVT()
    print 'hello world2'

vtpalmetto.name = 'repeatTrain'
vtpalmetto.main(task, [dict(), dict()])

