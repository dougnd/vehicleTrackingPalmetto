export RESULT_DIR=$HOME/results
export JOB_RESULT_DIR=$RESULT_DIR/pbs.${PBS_JOBID}
mkdir $JOB_RESULT_DIR

export INSTALL_DIR=${INSTALL_DIR:-$HOME/usr/local}
export GDAL_ROOT=$INSTALL_DIR

export gpuDev=$(qstat -f $PBS_JOBID | awk '/exec_vnode/ {
    match($0, /'`hostname`'\[([0-9]+)\]/, grp);
    print grp[1]
}')

echo "Using GPU: $gpuDev"
caffe device_query -gpu $gpuDev

function importResults {
    for f in "$@"
    do
        base=$(basename "$f")
        cp "$RESULT_DIR/$base" "$f"
    done
}

# use like:
# exportResults "src/caffe/mean.cvs" "src/caffe/vehicle_detector_train_iter_5000.caffemodel"
#
function exportResults {
    for f in "$@"
    do
        if [ -f "$f" ]; then
            base=$(basename "$f")
            cp "$f" "$JOB_RESULT_DIR"
            ln -fs "$JOB_RESULT_DIR/$base" "$RESULT_DIR/$base"
        else
            echo "Error: $f could not be exported because it does not exist!"
        fi
    done
}

