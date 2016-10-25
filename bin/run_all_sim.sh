#!/bin/bash
export INSTALL_DIR=${INSTALL_DIR:-$HOME/usr/local}

set -v

echo "new data!!!" >> ~/sim_results.csv

for f in /scratch2/dndawso/vehicleTracking/data/vehicleSimulation/*.csv ; do
    qsub -v file="$f",errorRate="0.0" $INSTALL_DIR/pbs/run_sim.pbs
    qsub -v file="$f",errorRate="0.05" $INSTALL_DIR/pbs/run_sim.pbs
    qsub -v file="$f",errorRate="0.1" $INSTALL_DIR/pbs/run_sim.pbs
done

