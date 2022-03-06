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
    cd "$scan/data"
    echo "$(pwd)"
    echo "Creating parsing directory..."
    mkdir -p parsing/stage{1..3}
    for file in $(ls batch-*)
    do
        # for each batch file, unzip
        batchName="${file%.tar.xz}"
        echo -e "\tUncompressing $batchName..."
        tar -Jxf $file
        echo -e "\tFinished Uncompressing $batchName"
        
        ########## do stage 1 ##########
        echo -e "\n\tStarting Stage 1..."
        python3 $parsingPATH/stage1/stage1-validate.py *Gecko* \
            > parsing/stage1/$batchName-stage1-parsed.json \
            2> parsing/stage1/$batchName-stage1-errors.json
        echo -e "\tFinished Stage 1"
        ########## end stage 1 ##########
        
        # IF errors, then we should stop... flag and move on?
        #fileSize=$(stat -c%s "parsing/stage1/$batchName-stage1-errors.json")
        fileSize=0
        if [ $fileSize -gt 0 ]
        then
            echo -e "\t$batchName stage 1 parsing error"
            # remove orignial files (still in zip)
            echo -e "\tRemoving raw Gecko Files..."
            rm *Gecko*
        else
            # remove orignial files (still in zip)
            echo -e "\tRemoving raw Gecko Files..."
            rm *Gecko*
            
            ########## do stage 2 ##########
            echo -e "\n\tStarting Stage 2..."
            python3 $parsingPATH/stage2/stage2-filter-3rd-parties.py \
                --input parsing/stage1/$batchName-stage1-parsed.json \
                --mapping $parsingPATH/dom-entity-dict.json \
                > parsing/stage2/$batchName-stage2-filtered.json
            echo -e "\tFinished Stage 2"
            ########## end stage 2 ##########
            # TODO: zipping this way creates the directory structure
            # parsing/stage1/zip.tar.xz which is obviously stupid - though it
            # won't lose any data, just make opening it again difficult
            #~~~~~~~~~~ zip stage 1 ~~~~~~~~~~
            echo -e "\tCompressing Stage 1 Output..."
            XZ_OPT="-v --threads=$zipThreads" tar -cJf \
                parsing/stage1/$batchName-stage1.tar.xz \
                --remove-files parsing/stage1/$batchName-stage1*
            echo -e "\tFinished Compressing Stage 1 Output"
            #~~~~~~~~~~ end zip stage 1 ~~~~~~~~~~
            
            ########## do stage 3 ##########
            echo -e "\n\tStarting Stage 3..."
            python3 $parsingPATH/stage3/stage3-filter-values.py \
                --globals $scanGLOBALS \
                --input parsing/stage2/$batchName-stage2-filtered.json \
                --output parsing/stage3/$batchName-stage3-filtered-values.json
            echo -e "\tFinished Stage 3"
            ########## end stage 3 ##########
            
            #~~~~~~~~~~ zip stage 2 ~~~~~~~~~~
            echo -e "\tCompressing Stage 2 Output..."
            XZ_OPT="-v --threads=$zipThreads" tar -cJf \
                parsing/stage2/$batchName-stage2.tar.xz \
                --remove-files parsing/stage2/$batchName-stage2*
            echo -e "\tFinished Compressing Stage 2 Output"
            #~~~~~~~~~~ end zip stage 2 ~~~~~~~~~~
        fi

    done
    # go back to starting location
    cd "$HOMEDIR"
done

