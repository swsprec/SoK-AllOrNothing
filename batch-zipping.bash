#!/bin/bash

##### GLOBALS #####
gigsize=1073741824 # 1GB in bytes 2^30

GIGNUM=100 # cutoff is 100 GB 
cutoff=$(( gigsize * GIGNUM )) 
HOMEDIR=$(pwd)

declare -a zipArray 
declare -a allFiles
##### END GLOBALS #####

# INput is scanID's e.g. ../YBZqB6 ../uyKeOR ...

for scan in "$@"
do 
    echo "Working on scan: $scan..."
    #declare -a zipArray 
    unset zipArray
    unset allFiles
    runningTotalSize=0
    batchCounter=0
    cd "$scan/data"
    echo "$(pwd)"
    for file in $(ls *)
    do
        fileSize=$(stat -c%s "$file")
        tmp=$(( runningTotalSize + fileSize  ))
        allFiles+=($file)
        if [ $tmp -gt $cutoff ]
        then
            # zip all files in array, reset arrary and runningTotal, add file to
            # array and runningTotal
            
            # do compressing and zipping
            echo -e "\tcompressing and zipping batch-$batchCounter"
            XZ_OPT="-v --threads=8" tar -cJf batch-$batchCounter.tar.xz ${zipArray[*]}
            
            unset zipArray
            unset runningTotalSize
            batchCounter=$(( batchCounter + 1 ))
        fi
        # add file to ziparray and increment runningTotal
        zipArray+=($file)
        runningTotalSize=$((runningTotalSize + fileSize))
    done
    echo -e "\tcompressing and zipping batch-$batchCounter"
    XZ_OPT="-v --threads=8" tar -cJf batch-$batchCounter.tar.xz ${zipArray[*]}

    # move all raw files to folder original & compress folder
    mkdir originals
    for fileAll in "${allFiles[@]}"
    do
        mv $fileAll originals/
    done
    echo -e "\tFiles moved to originals subdirectory"
    XZ_OPT="-v --threads=8" tar -cJf originals.tar.xz --remove-files originals/

    # go back to starting location
    cd "$HOMEDIR"
done
