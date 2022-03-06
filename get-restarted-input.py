#!/usr/bin/python3

import sys



originalInputFile = sys.argv[1]

# Need to generate this with command:
# $ cat RUNSEED-*-RunLog.json | jq -r ".site" > scannedSites.txt
sitesScannedFile = sys.argv[2]


originalList = []


with open(originalInputFile, "r") as original:
    for line in original:
        site = line.strip()
        originalList.append(site)

with open(sitesScannedFile, "r") as scanned:
    for line in scanned:
        site = line.strip()
        originalList.remove(site)

with open("NewInputList.txt", "w") as fout:
    for site in originalList:
        print(site, file=fout)

