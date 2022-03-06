#!/bin/bash

##### GLOBALS #####
parsingPATH="/home/swsprec/Documents/research/dataEx/parsing/"
HOMEDIR=$(pwd)
scanGLOBALS="/home/swsprec/Documents/research/dataEx/scan/study-scan-october-2020/crawler/globals.yml"
zipThreads="8"
##### END GLOBALS #####

# Input is scanID's e.g. ../YBZqB6 ../uyKeOR ...

for scan in "$@"
do 
    echo "Working on scan: $scan..."
    cd "$scan/data/parsing/stage2"
    echo "$(pwd)"

    # These are tar.xz files of stage2 output
    for file in $(ls batch-*)
    do
        # for each batch file, unzip
        batchName="${file%-stage2.tar.xz}"
        echo -e "\tUncompressing $batchName stage 2 output..."
        tar -Jxf $file
        echo -e "\tFinished Uncompressing $batchName stage 2 output"
        
        ########### do stage 2 ##########
        #echo -e "\n\tStarting Stage 2..."
        #python3 $parsingPATH/stage2/stage2-filter-3rd-parties.py \
        #    --input parsing/stage1/$batchName-stage1-parsed.json \
        #    --mapping $parsingPATH/dom-entity-dict.json \
        #    > parsing/stage2/$batchName-stage2-filtered.json
        #echo -e "\tFinished Stage 2"
        ########### end stage 2 ##########
        
        ########## do stage 3 ##########
        echo -e "\n\tStarting Stage 3..."
        python3 $parsingPATH/stage3/stage3-filter-values-exact.py \
            --globals $scanGLOBALS \
            --input parsing/stage2/$batchName-stage2-filtered.json \
            --output $batchName-stage3-filtered-values-exact.json
        mv *-$batchName-stage3-filtered-values-exact.json ../stage3/
        echo -e "\tFinished Stage 3"
        ########## end stage 3 ##########
       
        # Remove input file
        echo -e "\tRemoving stage2 files..."
        rm -r parsing/

    done
    # go back to starting location
    cd "$HOMEDIR"
done

