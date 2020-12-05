#!/usr/bin/env python3

import requests
import time
import xml.etree.ElementTree as xml
import json
import wx
import webbrowser
from os import listdir
from os.path import isfile
import re


def get_last_user():
    for f in listdir('.'):
        if isfile(f):
            z = re.match('^(.*?)_seen\\.json$', f)
            if z:
                return z.groups()[0]
    return ''


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
        user_name_sizer.Add(wx.StaticText(self, label="User Name"), 1, sizer_flags)
        self.user_name_entry = wx.TextCtrl(self)
        self.user_name_entry.SetValue(get_last_user())
        user_name_sizer.Add(self.user_name_entry, 1, sizer_flags)

        checkbox_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.owned_checkbox = wx.CheckBox(self, label="Own")
        self.owned_checkbox.SetValue(True)
        self.preordered_checkbox = wx.CheckBox(self, label="Preordered")
        self.preordered_checkbox.SetValue(True)
        checkbox_sizer.Add(self.owned_checkbox, 1, sizer_flags)
        checkbox_sizer.Add(self.preordered_checkbox, 1, sizer_flags)

        exp_type_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.expansions_checkbox = wx.CheckBox(self, label="Expansions")
        self.expansions_checkbox.SetValue(True)
        self.accessories_checkbox = wx.CheckBox(self, label="Accessories")
        self.accessories_checkbox.SetValue(True)
        self.reimplementations_checkbox = wx.CheckBox(self, label="Reimplementations")
        self.reimplementations_checkbox.SetValue(True)
        self.integrations_checkbox = wx.CheckBox(self, label="Integrations")
        self.integrations_checkbox.SetValue(True)
        exp_type_sizer.Add(self.expansions_checkbox, 1, sizer_flags)
        exp_type_sizer.Add(self.accessories_checkbox, 1, sizer_flags)
        exp_type_sizer.Add(self.reimplementations_checkbox, 1, sizer_flags)
        exp_type_sizer.Add(self.integrations_checkbox, 1, sizer_flags)

        retrieve_sizer = wx.BoxSizer(wx.HORIZONTAL)
        retrieve_button = wx.Button(self, label="Retrieve")
        retrieve_button.SetDefault()
        self.Bind(wx.EVT_BUTTON, self.download_data, retrieve_button)
        retrieve_sizer.Add(retrieve_button, 1, sizer_flags)

        self.main_sizer.Add(user_name_sizer, 1, sizer_flags)
        self.main_sizer.Add(checkbox_sizer, 1, sizer_flags)
        self.main_sizer.Add(exp_type_sizer, 1, sizer_flags)
        self.main_sizer.Add(retrieve_sizer, 1, sizer_flags)

        self.SetSizer(self.main_sizer)

        self.CreateStatusBar()
        self.SetStatusText("Ready")

    def download_data(self, event):

        user_name = self.user_name_entry.GetLineText(0)
        if user_name == "":
            self.SetStatusText("Missing user name")
            return

        statuses = []
        if self.owned_checkbox.GetValue():
            statuses.append("own")
        if self.preordered_checkbox.GetValue():
            statuses.append("preordered")

        types = []
        if self.expansions_checkbox.GetValue():
            types.append('boardgameexpansion')
        if self.accessories_checkbox.GetValue():
            types.append('boardgameaccessory')
        if self.reimplementations_checkbox.GetValue():
            types.append('boardgameimplementation')
        if self.integrations_checkbox.GetValue():
            types.append('boardgameintegration')

        if len(statuses) == 0:
            self.SetStatusText("Owned/Preordered not selected")
            return

        if len(types) == 0:
            self.SetStatusText("Expansions/Accessories/Reimplementations/Integrations not selected")
            return

        seen = []
        owned = []
        expansions = []

        self.SetStatusText("Getting collection data")
        status_code = 0
        while status_code != 200:
            resp = requests.get(self.collectionLink + user_name)
            status_code = resp.status_code
            if status_code == 202:
                self.SetStatusText("Collection request accepted. Will try again in " + str(self.sleep_duration) + " seconds.")
                time.sleep(self.sleep_duration)
            elif status_code != 200:
                self.SetStatusText("Unknown HTTP status code received: " + str(status_code) + ". Try again later.")
                return

        self.SetStatusText("Parsing collection data")
        root = xml.fromstring(resp.text)
        for child in root:
            status = child.find('status')
            consider = 0
            for sts in statuses:
                if status.get(sts) == '1':
                    consider = 1
                    break
            object_id = child.get('objectid')
            seen.append(object_id)
            if consider:
                owned.append(object_id)

        expansion_names = {}
        owned_appendix = ''
        i = 0
        for game in owned:
            owned_appendix += game + ','

            if i % self.expansions_per_request == self.expansions_per_request-1 or i == len(owned)-1:
                self.SetStatusText("Getting expansions: " + str(i+1) + "/" + str(len(owned)))
                resp = requests.get(self.ownedLink + owned_appendix)
                if resp.status_code != 200:
                    self.SetStatusText("Unknown HTTP status code received: " + str(resp.status_code) + ". Try again later.")
                    return

                root = xml.fromstring(resp.text)
                for child in root:
                    for item in types:
                        for expansion in child.findall(item):
                            expansions.append(expansion.get('objectid'))
                            expansion_names[expansion.get('objectid')] = expansion.text

                owned_appendix = ''

            i += 1

        try:
            with open(user_name+"_seen.json", "r") as file:
                seen += json.load(file)
        except:
            pass

        new_exp = []
        for exp in expansions:
            if exp not in seen:
                new_exp.append(exp)

        with open(user_name + "_expansions.html", "w") as html:
            html.write("""<html><head><link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@4.5.3/dist/css/bootstrap.min.css" integrity="sha384-TX8t27EcRE3e/ihU7zmQxVncDAy5uIKz4rEkgIXeMed4M0jlfIDPvg6uqKI2xXr2" crossorigin="anonymous"></head><body><div class="jumbotron text-center"><h1>News</h1><p>List of new expansions, reimplementations and accessories for your games</p></div>""")
            if len(new_exp) == 0:
                html.write("<div class='container'><div class='row'><div class='col-12'>No new expansions found.<br/>If you'd like to see all of the expansions again, delete <b>" + user_name + "_seen.json</b> file.</div></div></div>")
            else:
                html.write("<div class='container'>")
                meta_appendix = ''
                i = 0
                for exp in new_exp:
                    meta_appendix += exp + ','

                    if i % self.expansions_per_request == self.expansions_per_request-1 or i == len(new_exp)-1:
                        self.SetStatusText("Getting metadata: " + str(i+1) + "/" + str(len(new_exp)))
                        resp = requests.get(self.ownedLink + meta_appendix)
                        if resp.status_code != 200:
                            self.SetStatusText("Unknown HTTP status code received: " + str(resp.status_code) + ". Try again later.")
                            return

                        root = xml.fromstring(resp.text)
                        for child in root:
                            exp_thumbnail = ''
                            exp_id = child.get('objectid')
                            exp_name = expansion_names[exp_id]
                            for thumbnail in child.findall('thumbnail'):
                                if thumbnail.text is not None:
                                    exp_thumbnail = thumbnail.text
                            html.write("<div class='row'><div class='col-3'><img src=\"" + exp_thumbnail + "\"></img></div><div class='col-9'><a href=\"https://www.boardgamegeek.com/boardgame/" + exp_id + "\">" + exp_name + "</a></div></div>")

                        meta_appendix = ''

                    i += 1

                html.write("</div>")

        with open(user_name + "_seen.json", "w") as file:
            json.dump(expansions, file)

        webbrowser.open(user_name + "_expansions.html")

        self.SetStatusText("Finished")


if __name__ == "__main__":
    app = wx.App()
    gui = ExpGui(None, title="Expansion Checker")
    gui.Show()
    app.MainLoop()
