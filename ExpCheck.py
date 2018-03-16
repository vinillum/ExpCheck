#!/usr/bin/env python3

import requests
import time
import xml.etree.ElementTree as xml
import subprocess
import json

user_name = "vinillum"
expansions_per_request = 50
statuses = ["own", "preordered"]
sleep_duration = 10
ownedLink = 'https://www.boardgamegeek.com/xmlapi/boardgame/'
collectionLink = 'https://www.boardgamegeek.com/xmlapi/collection/'

seen = []
owned = []
expansions = {}

print("Getting collection data")
status_code = 0
while status_code != 200:
    resp = requests.get(collectionLink+user_name)
    status_code = resp.status_code
    if status_code == 202:
        print("Collection request accepted. Will try again in", sleep_duration, "seconds.")
        time.sleep(sleep_duration)
    elif status_code != 200:
        print("Unknown HTTP status code received: ")
        print(status_code)
        exit(1)

print("Parsing collection data")
root = xml.fromstring(resp.text)
for child in root:
    status = child.find('status')
    consider = 0
    for sts in statuses:
        if status.get(sts) == '1':
            consider = 1
            break
    if consider:
        object_id = child.get('objectid')
        object_text = child.find('name').text
        owned.append((object_id, object_text))
        seen.append(object_id)

ownedAppendix = ''
ownedText = ''
i = 0
for game in owned:
    i += 1
    ownedAppendix += game[0] + ','
    ownedText += '\n\t' + game[1]
    if i % expansions_per_request == expansions_per_request-1 or i == len(owned)-1:
        print("Getting expansions for " + ownedText)
        resp = requests.get(ownedLink + ownedAppendix)
        if resp.status_code != 200:
            print("Unknown HTTP status code received: ")
            print(resp.status_code)
            exit(1)

        root = xml.fromstring(resp.text)
        for child in root:
            for expansion in child.findall('boardgameexpansion'):
                expansions[expansion.get('objectid')] = expansion.text

        ownedAppendix = ''
        ownedText = ''

try:
    with open(user_name+"_seen_json", "r") as file:
        seen += json.load(file)
except:
    pass

json_exp = []
with open(user_name+"_expansions_json.html",  "w") as html:
    for exp, expName in expansions.items():
        json_exp.append(exp)
        if exp not in seen:
            html.write("<a href=\"https://www.boardgamegeek.com/boardgame/"+exp+"\">"+expName+"</a><br/>\n")

with open(user_name+"_seen_json", "w") as file:
    json.dump(json_exp, file)

subprocess.run(["chromium", user_name+"_expansions_json.html"])
