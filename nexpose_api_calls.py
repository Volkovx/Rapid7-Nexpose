'''
Copyright (c) 2022, Volkovx
All rights reserved.

This source code is licensed under the BSD-style license found in the
LICENSE file in the root directory of this source tree. 

This scripts pulls data from Rapid7's Nexpose API using various class methods (API calls), then saves pulled data into pandas dataframes and extract them to .csv format for the user.

__author__ = Volkovx
__github__ = https://github.com/Volkovx
__date__ = 08/14/2022
__version__ = 1.0
'''

import os
import csv
import json
import collections
import socket, struct
from timeit import default_timer as timer
import netaddr
import ipaddress
from datetime import datetime, timedelta, date
import datetime
import numpy as np
import pandas as pd
from io import StringIO
from io import BytesIO
from pathlib import Path
from getpass import getpass
from base64 import b64encode as b64e
from base64 import b64decode as b64d
from time import strftime
import itertools
import urllib3
import requests
from tqdm import tqdm
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from csv_diff import load_csv, compare

#Disable certificate warnings
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

class Main: # Class stores all needed Nexpose data as class attributes to then be used in various API calls.
    def __init__(self, host=None, auth=None, site_IDs=None, scanEngine_IDs=[], siteInfo=None,
                 scanSchedules=None, siteCreds=None, scanTemplates=None, scanEngines=None, enginePools=None,
                 users=None, console=None): 
        ''' 
        > Fucntion: instantiates the class (class constructor).
        > Input: user's Nexpose API credentials and API host to connect to. 

        '''
        # Nexpose configs:
        self.auth = auth # Stores encoded user credentials.
        self.host = host # Stores selected host URL.
        # DataFrames:
        self.siteInfo = siteInfo
        self.scanSchedules = scanSchedules
        self.siteCreds = siteCreds
        self.scanTemplates = scanTemplates
        self.scanEngines = scanEngines
        self.enginePools = enginePools
        self.users = users
        self.console = console
        # IDs:
        self.site_IDs = site_IDs # Stores all site IDs.
        self.scanEngine_IDs = scanEngine_IDs # Store scan engine IDs
        
        # Prompts user to select which Nexpose host to access.
        valid_hosts = {
            '1':['prod','LINK TO YOUR PRODUCTION API SERVER'],
            '2':['dev','LINK TO YOUR DEV ENVIRONEMENT API SERVER']}
        if host == None:
            selection = 0
            [print(x +': ' + valid_hosts[x][0] +' - ' + valid_hosts[x][1]) for x in valid_hosts.keys()]
            selection = input("Select which Nexpose API server you would like to access...\n"
                            +f"(Enter a number from {min(valid_hosts.keys())} to {max(valid_hosts.keys())})\n\n")
            if selection.strip() not in valid_hosts.keys():
                raise Exception(f'Wrong selection. Please select a number from {min(valid_hosts.keys())} to {max(valid_hosts.keys())}')
            self.host = valid_hosts[selection.strip()][1]
        elif host not in [valid_hosts[x][1] for x in valid_hosts.keys()]:
            raise Exception(f'Invalid hostname. This is not a known Nexpose API endpoint.')
        else:
            self.host = host # Stores specified Nexpose host as a Nexpose class attribute.
        # Prompts user for their Nexpose username and password:
        if auth == None: # Will always start as none.
            user = input("username: ")
            passw = b64e(getpass("password: ").encode()) # Encodes user password to not store it as clear text.
            self.auth = (user, passw) # Saves user credentials as a Nexpose class attributes (as a tuple).
            self.test_connection() # Tests your NEXPOSE credentials by testing them with your provided host. 
        else:
            self.auth = auth
           
    def get_auth(self):
        ''' 
        > Fucntion: Gets user's credentials (username and pass).

        '''
        return (self.auth[0],b64d(self.auth[1]).decode()) # Accesses the auth tuple and returns username and decoded password.
   
    def test_connection(self):
        ''' 
        > Fucntion: tests whether user credentials are correct or not by establishing a connection to the API server.

        '''
        url = f"{self.host}/sites"
        response = requests.get(url, auth=(self.auth[0],b64d(self.auth[1]).decode()), params={'page':0, 'size':1}, verify=False)
        try:
            response.raise_for_status()
        except:
            print(f'Unable to query API. Request returned error - {response.status_code}: {response.json()["message"]}')

    def get_siteIDs(self):
        ''' 
        > Fucntion: Gets and stores all Nexpose site IDs.

        '''
        print ("Getting all site IDs..") # Status update
        
        host = self.host
        url = f"{host}/sites" # Nexspose API databse URL (Assigns which part to access of the DB).
        response = requests.get(url, auth=self.get_auth(), params={'page':0, 'size':500}, verify=False)
        response.raise_for_status() # Reports back errors/issues.
        IDs = [x['id'] for x in response.json()['resources']] # Navigating through the output to get site IDs.
        self.site_IDs = IDs # Saving as a class attribute
    
    def get_siteInfo(self):
        ''' 
        > Fucntion: Gets and stores API data for site defaults (default template, scan engine, etc..

        '''
        print('Getting site specific info data..') # Status update
        
        dataframe = pd.DataFrame()
        for s_ID in self.site_IDs: 
            response = requests.get(self.host + f"/sites/{s_ID}",
                                    auth=self.get_auth(), params={'size':500}, verify=False) # Site alerts API call

            # Creating a dictionary that stores data sorted by site ID
            try:
                data = {'Site ID':s_ID,
                        'Number of Assets':(response.json()['assets']),
                        'Site Name':(response.json()['name']),
                        'Default Scan Engine':(response.json()['scanEngine']),
                        'Default Template':(response.json()['scanTemplate']),
                        'Site Type':(response.json()['type'])}
            except:
                pass
            # Saving data in a dataframe format
            dataframe = dataframe.append(data, ignore_index = True)
            dataframe = dataframe.replace(np.nan,'',regex=True) # Replaces all NaN/Null values with an empty string.
        convert = {'Site ID': int,
                   'Number of Assets': int}
        dataframe = dataframe.astype(convert)
        dataframe.sort_values(by=['Site ID'])
        self.siteInfo = dataframe # Saving as a class attribute.
        self.siteInfo.drop_duplicates(keep=False)
        
    def get_scanSchedules(self):
        ''' 
        > Fucntion: Gets and stores API data for site scan schedules.

        '''
        print('Getting site scan-schedules data..') # Status update
        
        scans_df = pd.DataFrame()
        for s_ID in self.site_IDs: # Iterates through all Nexpose sites and gets their scan-schedule targets.
            all_scans_response = requests.get(self.host + f"/sites/{s_ID}/scan_schedules",
                                              auth=self.get_auth(), params={'size': 500}, verify=False) # Scan sched. API call.
            for item in all_scans_response.json()['resources']: # Interprets through output and fills 'data' dictionary.  
                # A dictionary that stores data sorted by site ID
                try:
                    data = {'Duration of Scan':item['duration']}
                except:
                    pass
                try:
                    data = {'Site ID':s_ID,
                            'Enabled':item['enabled'],
                            'Scan Schedule ID':item['id'],
                            'Scan Name':item['scanName'],
                            'Scan Template ID':item['scanTemplateId'],
                            'Scan Engine ID':item['scanEngineId'],
                            'Included Assets':None,
                            'Excluded Assets':None,
                            'Start Time':item['start']}               
                except:
                    data = {'Site ID':s_ID,
                            'Enabled':item['enabled'],
                            'Scan Schedule ID':item['id'],
                            'Scan Name':item['scanName'],
                            'Scan Template ID':item['scanTemplateId'],
                            'Included Assets':None,
                            'Excluded Assets':None,
                            'Start Time':item['start']} 
                try:
                    if 'includedTargets' in item['assets'].keys():
                        data['Included Assets'] = set(item['assets']['includedTargets']['addresses']) # Stores inc targets to 'data'.

                    if 'excludedTargets' in item['assets'].keys():
                        data['Excluded Assets'] = set(item['assets']['excludedTargets']['addresses']) # Stores exc targets to 'data'.
                except:
                    pass
                # Appending 'data' dict into a dataframe: 
                scans_df = scans_df.append(data, ignore_index=True) 
                scans_df = scans_df.replace(np.nan,'',regex=True) # Replaces all NaN/Null values with an empty string.

        self.scanSchedules = scans_df # Saving as a class attribute.
    
    def get_siteCreds(self):
        ''' 
        > Fucntion: Gets and stores API data for site shared credentials.

        '''
        print('Getting site credentials data..') # Status update
        
        dataframe = pd.DataFrame()
        for s_ID in self.site_IDs:
            siteCreds = requests.get(self.host + f"/sites/{s_ID}/shared_credentials",
                                      auth=self.get_auth(), params={'size':500}, verify=False) # Site alerts API call
            site_name = requests.get(self.host + f"/sites/{s_ID}",
                           auth=self.get_auth(), params={'size': 500}, verify=False) # Gets site name
            
            # Creating a dictionary that stores data sorted by site ID
            for item in siteCreds.json()['resources']:
                data = {'Site ID':s_ID,
                        'Site Name': None,
                        'Site Credential Enabled?':item['enabled'],
                        'Credential Name':item['name'],
                        'Credential ID':item['id'],
                        'Credential Service':item['service']}
                data['Site Name'] = site_name.json()['name']
                # Saving data in a dataframe format
                dataframe = dataframe.append(data, ignore_index = True)
                dataframe = dataframe.replace(np.nan,'',regex=True) # Replaces all NaN/Null values with an empty string.
        convert = {'Site ID': int}
        dataframe = dataframe.astype(convert)
        dataframe.sort_values(by=['Site ID'])
        self.siteCreds = dataframe # Saving as a class attribute.
    
    def get_scanTemplates(self):
        ''' 
        > Fucntion: Gets and stores API data for scan templates.

        '''
        print("Getting scan templates data..") # Status update
        
        dataframe = pd.DataFrame()
        url = self.host + f"/scan_templates"                               
        response = requests.get(url, auth=self.get_auth(), params={'page':0, 'size':500}, verify=False)
        response.raise_for_status()
        output = response.json()['resources']
        # Creating a dictionary that stores data
        for item in output:
            try:
                data={'Scan Template Name':item['name'],
                      'Scan Template ID':item['id'],
                      'Description':item['description'],
                      'Discovery Only?': item['discoveryOnly'],
                      'Vulnerability Enabled?':item['vulnerabilityEnabled'],
                      'Policy Enabled?':item['policyEnabled'],
                      'Policy':item['policy'],
                      'Web Enabled?':item['webEnabled'],
                      'Web':item['web'],
                      'Windows Services Enabled?':item['enableWindowsServices'],
                      'Enhanced Logging?':item['enhancedLogging'],
                      'Max Parallel Assets':item['maxParallelAssets'],
                      'Max Scan Processes':item['maxScanProcesses'],
                      'Telnet':item['telnet']}
            except KeyError:
                data={'Scan Template Name':item['name'],
                      'Scan Template ID':item['id'],
                      'Description':item['description'],
                      'Discovery Only?': item['discoveryOnly'],
                      'Vulnerability Enabled?':item['vulnerabilityEnabled'],
                      'Policy Enabled?':item['policyEnabled'],
                      'Web Enabled?':item['webEnabled'],
                      'Windows Services Enabled?':item['enableWindowsServices'],
                      'Enhanced Logging?':item['enhancedLogging'],
                      'Max Parallel Assets':item['maxParallelAssets'],
                      'Max Scan Processes':item['maxScanProcesses'],
                      'Telnet':item['telnet']}
            # Saving data in a dataframe format
            dataframe = dataframe.append(data, ignore_index = True)
            dataframe = dataframe.replace(np.nan,'',regex=True) # Replaces all NaN/Null values with an empty string.
        convert = {'Scan Template ID': str,
                   'Discovery Only?': bool,
                   'Enhanced Logging?': bool,
                   'Policy Enabled?': bool,
                   'Vulnerability Enabled?': bool,
                   'Web Enabled?': bool,
                   'Windows Services Enabled?': bool}
        dataframe = dataframe.astype(convert)
        dataframe.sort_values(by=['Scan Template ID'])
        self.scanTemplates = dataframe # Saving as a class attribute.
    
    def get_scanEngines(self):
        ''' 
        > Fucntion: Gets and stores API data for scan engines.

        '''
        print("Getting scan engines data..") # Status update
        
        dataframe = pd.DataFrame()
        url = self.host + "/scan_engines"
        response = requests.get(url, auth=self.get_auth(), params={'page':0, 'size':500}, verify=False)
        response.raise_for_status()
        output = response.json()['resources']
        # Creating a dictionary that stores data:
        for item in output:
            try:
                data={'Scan Engine ID':item['id'],
                      'Scan Engine Name':item['name'],
                      'Sites':item['sites'],
                      'Address':item['address'],
                      'Port':item['port'],
                      'Content Version':item['contentVersion'],
                      'Product Version':item['productVersion']}
            except:
                data={'Scan Engine ID':item['id'],
                      'Scan Engine Name':item['name'],
                      #'Sites':item['sites'],
                      'Address':item['address'],
                      'Port':item['port'],
                      'Content Version':item['contentVersion'],
                      'Product Version':item['productVersion']}
            # Appending 'data' dict into a dataframe:
            dataframe = dataframe.append(data, ignore_index = True)
            dataframe = dataframe.replace(np.nan,'',regex=True) # Replaces all NaN/Null values with an empty string.
            
        convert = {'Scan Engine ID': int}
        dataframe = dataframe.astype(convert)
        dataframe.sort_values(by=['Scan Engine ID'])
        self.scanEngines = dataframe # Saving as a class attribute.
        for item in self.scanEngines['Scan Engine ID']: # Saving scan engine IDs as a class attribute
            self.scanEngine_IDs.append(round(item))
            
    def get_enginePools(self):
        ''' 
        > Fucntion: Gets and stores Nexpose API data for all available scan engine pools.

        '''
        print("Getting scan engine pools data..") # Status update
        
        dataframe = pd.DataFrame()
        url = self.host + "/scan_engine_pools"
        response = requests.get(url, auth=self.get_auth(), params={'page':0, 'size':500}, verify=False)
        response.raise_for_status()
        output = response.json()['resources']
        # Creating a dictionary that stores data:
        for item in output:
            try:
                data={'Pool ID':item['id'],
                      'Pool Name':item['name'],
                      'Pool Engines':item['engines']}
            except:
                pass
            # Appending 'data' dict into a dataframe:
            dataframe = dataframe.append(data, ignore_index = True)
            dataframe = dataframe.replace(np.nan,'',regex=True) # Replaces all NaN/Null values with an empty string.
            
        convert = {'Pool ID': int}
        dataframe = dataframe.astype(convert)
        dataframe.sort_values(by=['Pool Name'])
        self.enginePools = dataframe # Saving as a class attribute.
    
    def get_users(self):
        '''
            > Function: Gets names and IDs of all users on Nexpose
        '''
        host = self.host
        dataframe = pd.DataFrame() # Empty dataframe

        print("Getting Nexpose users info..") # Status update

        url = f"{host}/users" # Nexspose API databse URL (Assigns which part to access of the DB).
        response = requests.get(url, auth=self.get_auth(), params={'page':0, 'size':500}, verify=False)
        response.raise_for_status() # Reports back errors/issues.

        data = {'User Name':None,
                'User ID':None}

        for item in response.json()['resources']:
            try:
                data['User Name'] = item['name']
            except:
                pass
            try:
                data['User ID'] = item['id']
            except:
                pass
            dataframe = dataframe.append(data, ignore_index=True) # Appending data's info to a dataframe
            dataframe = dataframe.replace(np.nan,'',regex=True)

        # Sorts the dataframe by a certain column:
        convert = {'User ID': int}
        dataframe = dataframe.astype(convert) # Ensure IDs are 'int' datatype
        dataframe.sort_values(by=['User ID'])
        self.users = dataframe # Saving as a class attribute.
    
    def get_consoleInfo(self):
        '''
            > Function: Gets console version info
        '''
        host = self.host
        dataframe = pd.DataFrame() # Empty dataframe

        print("Getting Nexpose console info..") # Status update

        url = f"{host}/administration/info" # Nexspose API databse URL (Assigns which part to access of the DB).
        response = requests.get(url, auth=self.get_auth(), params={'page':0, 'size':500}, verify=False)
        response.raise_for_status() # Reports back errors/issues.

        data = {'Content Version':None,
                'Content Version (Partial)':None,
                'Product ID':None,
                'Version ID':None,
                'Product':None}

        response_dict = response.json()['version']['update']

        try:
            data['Content Version'] = response_dict['content']
        except:
            pass
        try:
            data['Content Version (Partial)'] = response_dict['contentPartial']
        except:
            pass
        try:
            data['Product ID'] = response_dict['id']['productId']
        except:
            pass
        try:
            data['Version ID'] = response_dict['id']['versionId']
        except:
            pass
        try:
            data['Product'] = response_dict['product']
        except:
            pass
        dataframe = dataframe.append(data, ignore_index=True) # Appending data's info to a dataframe
        dataframe = dataframe.replace(np.nan,'',regex=True)

        self.console = dataframe # Saving as a class attribute.
    
    def save_data(self):
        ''' 
        > Functionality: Saves all API data retrieved as .pkl files at the 'Data' directory.

        '''
        print("Saving Nexpose API data as CSV files..")
        date_today = date(day=int(strftime('%d')), month=int(strftime('%m')), year=int(strftime('%Y'))).strftime('%Y-%m-%d') # Gets current date and time
        # Creating the correctly formatted directory for nexpose data:
        directory = f'{date_today}'
        parent_dir = f'C:\\YourDirectory\\Nexpose\\Data\\'
        path = os.path.join(parent_dir, directory)
        try:
            os.mkdir(path)
        except FileExistsError:
            pass
        
        # Saving data as CSV:
        self.siteCreds.to_csv(f"Data/{date_today}/Site_Credentials_Configs.csv", index = False, header = True)
        self.siteInfo.to_csv(f"Data/{date_today}/Site_Defaults.csv", index = False, header = True)
        self.scanSchedules.to_csv(f"Data/{date_today}/Scan_Schedules_Configs.csv", index = False, header = True)
        self.scanEngines.to_csv(f"Data/{date_today}/Scan_Engines_Configs.csv", index = False, header = True)
        self.enginePools.to_csv(f"Data/{date_today}/Engine_Pools_Configs.csv", index = False, header = True)
        self.scanTemplates.to_csv(f"Data/{date_today}/Scan_Templates_Configs.csv", index = False, header = True)
        self.users.to_csv(f"Data/{date_today}/Users.csv", index = False, header = True)
        self.console.to_csv(f"Data/{date_today}/Console_Info.csv", index = False, header = True)
        print('CSV files saved under "Data" directory')
        
    def loader(self):
        '''
        > Fucntion: Loads above methods to populate class attributes
        '''
        start = timer()
        self.get_siteIDs()
        self.get_siteAssets()
        self.get_siteInfo()
        self.get_scanSchedules()
        self.get_siteCreds()
        self.get_scanTemplates()
        self.get_scanEngines()
        self.get_enginePools()
        self.get_users()
        self.get_consoleInfo()
        self.save_data()
        end = timer()
        print("\nAll done! code execution time: ",round((end-start)/60)," minute(s)")


main = Main() # Instantiates an object of the 'Main()' class
main.loader() # Runs all above methods/API calls
