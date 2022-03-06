#!/usr/bin/python3

import json
import os
import sys

tracker_radar_folder = sys.argv[1]

if not tracker_radar_folder:
    print("Usage: python3 %s <tracker-radar folder location>" % sys.argv[0])
    sys.exit(1)

entity_folder = tracker_radar_folder + "/entities"

dom_to_entity = {}

for entry in os.scandir(entity_folder):
    with open(entry.path, "r") as jsonIn:
        try:
            data = json.load(jsonIn)

            for domain in data['properties']:
                if domain in dom_to_entity:
                    continue
                else:
                    dom_to_entity[domain] = data['displayName']
        except ValueError as e:
            pass

with open("dom-entity-dict.json", "w") as fout:
    print(json.dumps(dom_to_entity), file=fout)
