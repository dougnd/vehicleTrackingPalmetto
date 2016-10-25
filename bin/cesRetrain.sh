#!/bin/bash

export RESULT_DIR=$HOME/results

export INSTALL_DIR=${INSTALL_DIR:-$HOME/usr/local}
export GDAL_ROOT=$INSTALL_DIR

export gpuDev=0


dataset=${dataset:-skycomp1}
x=${x:-0}
y=${y:-0}
w=${w:-5300}
h=${h:-3500}
testFrames=${testFrames:-"10 11 12 13 14"}
trainFrames=${trainFrames:-"0 1 2 3 4 5 6 7 8 9"}
n=${n:-20}
sz=${sz:-200}

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

function runIter {
    export JOB_RESULT_DIR=$RESULT_DIR/iter$1
    mkdir $JOB_RESULT_DIR

    if [ -f detections.pb ]; then
        echo "Got old results..."
        detectionInfo="-d detections.pb"
    fi

    rm -rf src/caffe/*.leveldb
    util/labeledDataToDB -l $dataset $detectionInfo -n negatives.yml -t "$trainFrames" -T "$testFrames"
    make trainNet

    make basicDetector
    make buildNet
    util/basicDetector -r $x $y $w $h -s $sz -n $n $dataset
    make detectionAccuracy
    util/detectionAccuracy -l $dataset -d detections.pb -t "$trainFrames" -T "$testFrames" > accuracy.txt

    exportResults "src/caffe/mean.cvs" "src/caffe/vehicle_detector_train_iter_5000.caffemodel" "negatives.yml" "detections.pb" "accuracy.txt"
}

if [ -z $1 ]; then
    echo "Put number of times to repeat as argument"
    exit 1
fi

for i in $(seq 1 $1); do
    echo "---------------------------------------------------------------"
    echo " ITERATION: $i "
    echo "---------------------------------------------------------------"

    runIter $i
done
