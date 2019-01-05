#!/usr/bin/env python3

import requests
import time
import xml.etree.ElementTree as xml
import subprocess
import json
import wx


class ExpGui(wx.Frame):

    expansions_per_request = 50
    sleep_duration = 10
    ownedLink = 'https://www.boardgamegeek.com/xmlapi/boardgame/'
    collectionLink = 'https://www.boardgamegeek.com/xmlapi/collection/'

    def __init__(self, *args, **kw):
        super(ExpGui, self).__init__(*args, **kw)

        sizer_flags = wx.EXPAND | wx.ALIGN_CENTER

        self.main_sizer = wx.BoxSizer(wx.VERTICAL)

        user_name_sizer = wx.BoxSizer(wx.HORIZONTAL)
        user_name_sizer.Add(wx.StaticText(self, label="User Name"))
        self.user_name_entry = wx.TextCtrl(self)
        user_name_sizer.Add(self.user_name_entry, sizer_flags, sizer_flags)

        checkbox_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.owned_checkbox = wx.CheckBox(self, label="Own")
        self.preordered_checkbox = wx.CheckBox(self, label="Preordered")
        checkbox_sizer.Add(self.owned_checkbox, sizer_flags, sizer_flags)
        checkbox_sizer.Add(self.preordered_checkbox, sizer_flags, sizer_flags)

        retrieve_sizer = wx.BoxSizer(wx.HORIZONTAL)
        retrieve_button = wx.Button(self, label="Retrieve")
        self.Bind(wx.EVT_BUTTON, self.download_data, retrieve_button)
        retrieve_sizer.Add(retrieve_button, sizer_flags, sizer_flags)

        self.main_sizer.Add(user_name_sizer, sizer_flags, sizer_flags)
        self.main_sizer.Add(checkbox_sizer, sizer_flags, sizer_flags)
        self.main_sizer.Add(retrieve_sizer, sizer_flags, sizer_flags)

        self.SetSizer(self.main_sizer)

        self.CreateStatusBar()
        self.SetStatusText("Ready")

    def download_data(self, event):

        user_name = self.user_name_entry.GetLineText(0)
        if user_name == "":
            return

        statuses = []
        if self.owned_checkbox.GetValue():
            statuses.append("own")
        if self.preordered_checkbox.GetValue():
            statuses.append("preordered")

        if len(statuses) == 0:
            return

        seen = []
        owned = []
        expansions = {}

        self.SetStatusText("Getting collection data\n")
        status_code = 0
        while status_code != 200:
            resp = requests.get(self.collectionLink+user_name)
            status_code = resp.status_code
            if status_code == 202:
                self.SetStatusText("Collection request accepted. Will try again in " + str(self.sleep_duration) + " seconds.\n")
                time.sleep(self.sleep_duration)
            elif status_code != 200:
                self.SetStatusText("Unknown HTTP status code received: "+str(status_code))
                exit(1)

        self.SetStatusText("Parsing collection data\n")
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
                self.SetStatusText("Getting expansions: " + str(i) + "/" + str(len(owned)))
                resp = requests.get(self.ownedLink + owned_appendix)
                if resp.status_code != 200:
                    self.SetStatusText("Unknown HTTP status code received: " + str(resp.status_code))
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

        self.SetStatusText("Finished")

        subprocess.run(["chromium", user_name+"_expansions_json.html"])


if __name__ == "__main__":
    app = wx.App()
    gui = ExpGui(None, title="Expansion Checker")
    gui.Show()
    app.MainLoop()
