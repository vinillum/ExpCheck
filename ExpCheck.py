#!/usr/bin/env python3

import requests
import time
import xml.etree.ElementTree as xml
import subprocess
import json
import tkinter
import threading


class ExpGui:

    expansions_per_request = 50
    sleep_duration = 10
    ownedLink = 'https://www.boardgamegeek.com/xmlapi/boardgame/'
    collectionLink = 'https://www.boardgamegeek.com/xmlapi/collection/'

    def __init__(self, gui_master):
        self.gui_master = gui_master;
        self.gui_master.title("ExpCheck")
        tkinter.Label(self.gui_master, text="User Name").grid(row=0, column=0)
        self.username_entry = tkinter.Entry(self.gui_master)
        self.username_entry.grid(row=0, column=1)
        self.own_checkbox = tkinter.IntVar()
        tkinter.Checkbutton(self.gui_master, text="Own", variable=self.own_checkbox).grid(row=1, column=0)
        self.preordered_checkbox = tkinter.IntVar()
        tkinter.Checkbutton(self.gui_master, text="Preordered", variable=self.preordered_checkbox).grid(row=1, column=1)
        tkinter.Button(self.gui_master, text="Retrieve", command=self.download_data).grid(row=2, column=0, columnspan=2)

    def download_data(self):
        connection_thread = threading.Thread(target=lambda: self.download_data2())
        connection_thread.start()

    def download_data2(self):

        user_name = self.username_entry.get()
        if user_name == "":
            return

        statuses = []
        if self.own_checkbox.get():
            statuses.append("own")
        if self.preordered_checkbox.get():
            statuses.append("preordered")

        if len(statuses) == 0:
            return

        text_box = tkinter.Text(self.gui_master)
        text_box.grid(row=3, column=0, columnspan=2, rowspan=10)

        seen = []
        owned = []
        expansions = {}

        text_box.insert(tkinter.END, "Getting collection data\n")
        status_code = 0
        while status_code != 200:
            resp = requests.get(self.collectionLink+user_name)
            status_code = resp.status_code
            if status_code == 202:
                text_box.insert(tkinter.END, "Collection request accepted. Will try again in " + str(self.sleep_duration) + " seconds.\n")
                time.sleep(self.sleep_duration)
            elif status_code != 200:
                text_box.insert(tkinter.END, "Unknown HTTP status code received: ")
                text_box.insert(tkinter.END, status_code)
                exit(1)

        text_box.insert(tkinter.END, "Parsing collection data\n")
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

        owned_appendix = ''
        owned_text = ''
        i = 0
        for game in owned:
            i += 1
            owned_appendix += game[0] + ','
            owned_text += '\n\t' + game[1]
            if i % self.expansions_per_request == self.expansions_per_request-1 or i == len(owned)-1:
                text_box.insert(tkinter.END, "Getting expansions for " + owned_text)
                resp = requests.get(self.ownedLink + owned_appendix)
                if resp.status_code != 200:
                    text_box.insert(tkinter.END, "Unknown HTTP status code received: ")
                    text_box.insert(tkinter.END, resp.status_code)
                    exit(1)

                root = xml.fromstring(resp.text)
                for child in root:
                    for expansion in child.findall('boardgameexpansion'):
                        expansions[expansion.get('objectid')] = expansion.text

                owned_appendix = ''
                owned_text = ''

        try:
            with open(user_name+"_seen.json", "r") as file:
                seen += json.load(file)
        except:
            pass

        json_exp = []
        with open(user_name+"_expansions_json.html",  "w") as html:
            for exp, expName in expansions.items():
                json_exp.append(exp)
                if exp not in seen:
                    html.write("<a href=\"https://www.boardgamegeek.com/boardgame/"+exp+"\">"+expName+"</a><br/>\n")

        with open(user_name+"_seen.json", "w") as file:
            json.dump(json_exp, file)

        subprocess.run(["chromium", user_name+"_expansions_json.html"])


gui_master = tkinter.Tk()
ExpGui(gui_master)
gui_master.mainloop()
