#!/usr/bin/env python3

import requests
import time
import xml.etree.ElementTree as xml
import json
import wx
import webbrowser


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
        self.owned_checkbox.SetValue(True)
        self.preordered_checkbox = wx.CheckBox(self, label="Preordered")
        self.preordered_checkbox.SetValue(True)
        checkbox_sizer.Add(self.owned_checkbox, sizer_flags, sizer_flags)
        checkbox_sizer.Add(self.preordered_checkbox, sizer_flags, sizer_flags)

        exp_type_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.expansions_checkbox = wx.CheckBox(self, label="Expansions")
        self.expansions_checkbox.SetValue(True)
        self.accessories_checkbox = wx.CheckBox(self, label="Accessories")
        self.accessories_checkbox.SetValue(True)
        self.reimplementations_checkbox = wx.CheckBox(self, label="Reimplementations")
        self.reimplementations_checkbox.SetValue(True)
        exp_type_sizer.Add(self.expansions_checkbox, sizer_flags, sizer_flags)
        exp_type_sizer.Add(self.accessories_checkbox, sizer_flags, sizer_flags)
        exp_type_sizer.Add(self.reimplementations_checkbox, sizer_flags, sizer_flags)

        retrieve_sizer = wx.BoxSizer(wx.HORIZONTAL)
        retrieve_button = wx.Button(self, label="Retrieve")
        retrieve_button.SetDefault()
        self.Bind(wx.EVT_BUTTON, self.download_data, retrieve_button)
        retrieve_sizer.Add(retrieve_button, sizer_flags, sizer_flags)

        self.main_sizer.Add(user_name_sizer, sizer_flags, sizer_flags)
        self.main_sizer.Add(checkbox_sizer, sizer_flags, sizer_flags)
        self.main_sizer.Add(exp_type_sizer, sizer_flags, sizer_flags)
        self.main_sizer.Add(retrieve_sizer, sizer_flags, sizer_flags)

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

        if len(statuses) == 0:
            self.SetStatusText("Owned/Preordered not selected")
            return

        if len(types) == 0:
            self.SetStatusText("Expansions/Accessories/Reimplementations not selected")
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
            if len(new_exp) == 0:
                html.write("No new expansions found.<br/>If you'd like to see all of the expansions again, delete " + user_name + "_seen.json file.")
            else:
                html.write("<table border=1>")
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
                            html.write("<tr><td><img src=\"" + exp_thumbnail + "\"></img></td><td><a href=\"https://www.boardgamegeek.com/boardgame/" + exp_id + "\">" + exp_name + "</a></td></tr>")

                        meta_appendix = ''

                    i += 1

                html.write("</table>")

        with open(user_name + "_seen.json", "w") as file:
            json.dump(expansions, file)

        webbrowser.open(user_name + "_expansions.html")

        self.SetStatusText("Finished")


if __name__ == "__main__":
    app = wx.App()
    gui = ExpGui(None, title="Expansion Checker")
    gui.Show()
    app.MainLoop()
