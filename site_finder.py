'''
Copyright (c) 2022, Volkovx
All rights reserved.
This source code is licensed under the BSD-style license found in the
LICENSE file in the root directory of this source tree. 

This script pulls all Nexpose site included & excluded targets, then proceeds to compare provided IP address (entered by the user) or addresses (using a .txt file) to find the correct site they are under.

__author__ = Volkovx
__github__ = https://github.com/Volkovx
__date__ = 08/14/2022
__version__ = 1.0
'''



import pandas as pd
import numpy as np
import socket, struct
import csv
import os
import datetime
from datetime import datetime, timedelta, date
from time import strftime
from getpass import getpass
from base64 import b64encode as b64e
from base64 import b64decode as b64d
import urllib3
import requests
from timeit import default_timer as timer
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

os.getcwd()

class Main:
    def __init__(self, host=None, auth=None, site_IDs=None,
                 site_targets=[], scan_actuals=[]): 
        ''' 
        > Functionality: class constructor.
        > Input: takes user's Nexpose API credentials and which API host to connect to. 

        '''
        # Nexpose configs:
        self.auth = auth # Stores encoded user credentials.
        self.host = host # Stores selected host URL.
        # DataFrames:
        self.site_targets = site_targets # Stores site targets dataframe.
        self.scan_actuals = scan_actuals
        # IDs:
        self.site_IDs = site_IDs # Stores all site IDs.
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
        if auth == None:
            user = input("username: ")
            passw = b64e(getpass("password: ").encode())
            self.auth = (user, passw) # Saves user credentials as a Nexpose class attributes (as a tuple).
            self.test_connection()
        else:
            self.auth = auth
           
    ### GETS DECODED USER CREDENTIALS ### --> |CALLED: when class object is instantiated.|
    def get_auth(self):
        ''' 
        > Functionality: Gets user's credentials (username and pass).

        '''
        return (self.auth[0],b64d(self.auth[1]).decode())
   
    ### TESTS USER'S CONNECTION TO HOST ###
    def test_connection(self):
        ''' 
        > Functionality: tests whether user credentials are correct or not by establishing a connection to the API server.

        '''
        url = f"{self.host}/sites"
        response = requests.get(url, auth=(self.auth[0],b64d(self.auth[1]).decode()), params={'page':0, 'size':1}, verify=False)
        try:
            response.raise_for_status()
        except:
            print(f'Unable to query API. Request returned error - {response.status_code}: {response.json()["message"]}')
    
    def IP_rangeSplitter(self, ip_range): # --> |INPUT: a tuple (start, end) of the IP range.|
        if ' - ' in ip_range: # user provided an IP range
            IP_range = tuple(ip_range.split(' - '))
            start = IP_range[0] 
            end = IP_range[1]
            start = struct.unpack('>I', socket.inet_aton(start))[0]
            end = struct.unpack('>I', socket.inet_aton(end))[0]
            return [socket.inet_ntoa(struct.pack('>I', i)) for i in range(start, end+1)] # Returns all IPs within the range.
        else: # user didn't provide an IP range
            return ip_range
    
    def get_siteIDs(self):
        ''' 
        > Functionality: Gets and stores all Nexpose site IDs.

        '''
        print ("\nGetting all site IDs..")
        host = self.host
        url = f"{host}/sites" # Nexspose API databse URL (Assigns which part to access of the DB).
        response = requests.get(url, auth=self.get_auth(), params={'page':0, 'size':500}, verify=False)
        response.raise_for_status() # Reports back errors/issues.
        IDs = [x['id'] for x in response.json()['resources']] # Navigating through the output to get site IDs.
        self.site_IDs = IDs # Saving as a class attribute 
    
    def get_site_targets(self):
        ''' 
        > Functionality: Gets and stores API data for sites targets (inclusions & exclusions).

        '''
        print('Getting site targets data..')
        sites_df = pd.DataFrame()
        
        for s_ID in self.site_IDs: # Gets inc/exc targets for all sites (interpreting site-by-site).
            incTargets = []
            excTargets = []
            included_assets = requests.get(self.host + f"/sites/{s_ID}/included_targets",
                                           auth=self.get_auth(), params={'size': 500}, verify=False) # Inc targets API call.
            excluded_assets = requests.get(self.host + f"/sites/{s_ID}/excluded_targets",
                                           auth=self.get_auth(), params={'size': 500}, verify=False) # Exc targets API call.
            site_name = requests.get(self.host + f"/sites/{s_ID}",
                                           auth=self.get_auth(), params={'size': 500}, verify=False) # Gets site name
            # Creates a dictionary that stores data sorted by site ID:
            data = {'Site ID': round(s_ID),
                    'Site Name':None,
                    'Included Targets':None,
                    'Excluded Targets':None,}
            data['Site Name'] = site_name.json()['name']
            try:
                out_data = included_assets.json()['addresses']
                for item in out_data:
                    incTargets.append((self.IP_rangeSplitter(item)))
                data['Included Targets'] = incTargets
            except:
                pass
            
            try:
                out_data = excluded_assets.json()['addresses']
                for item in out_data:
                    excTargets.append((self.IP_rangeSplitter(item)))
                data['Excluded Targets'] = excTargets
            except:
                pass
            sites_df = sites_df.append(data, ignore_index = True)
            sites_df = sites_df.replace(np.nan,'',regex=True) # Replaces all NaN/Null values with an empty string.
            sites_df.sort_values(by=['Site ID'])
        convert = {'Site ID': int}
        sites_df = sites_df.astype(convert)
        sites_df.sort_values(by=['Site ID'])
        self.site_targets = sites_df # Saving as a class attribute.
    
    def flatten(self, List):
        flat = []
        for item in List:
            for sub in item:
                flat.append(sub)
        return flat
    
    def loader(self):
        start = timer()
        main.get_siteIDs()
        main.get_site_targets()
        end = timer()
        print("\nAll done! code execution time: ",round((end-start)/60)," minute(s)")

###################################################################### Script Runner ##################################################################################

main = Main() # Creates an object of the 'Main' class
main.loader() # Loads Main class's methods

IP = 1
IPs_path = 1

while True:
    selection = int(input("Please select operation (1) or (2):\n  >> Type '1' for checking a single IP adrress.\n  >> Type '2' for checking a list of IP addresses.\n"))
    if selection == 1:
        IP = str(input("Please enter the IP address you would like to check:\n"))
        IPs_path = None
        break

    elif selection == 2:
        IPs_path = str(input("Please type the full file path to your IP addreses list (have each IP address separated by a newline):"))
        IP = None
        break

    else:
        print("Wrong selection, select either operation 1 or 2. Terminating the program..")
        break

if IPs_path == None: # User chose to look-up one IP address
    start = timer() # To time how long the code takes to run
    now = datetime.now() # Getting today's date & time
    date_str = now.strftime("%m-%d-%Y_T%H-%M-%S") # Creating date-time string
    IP = IP
    info = main.site_targets.copy() # Making a copy of the site targets api call dataframe
    info = info[['Site Name', 'Included Targets', 'Excluded Targets']] # Filtering the dataframe for needed columns

    inc_data = {  
        'Inc':None,
        'Site':None
    }
    exc_data = {
        'Exc':None,
        'Site':None
    }
    output = {}
    inc_list = []
    exc_list = []

    for inc, exc, site in zip(info['Included Targets'], info['Excluded Targets'], info['Site Name']):
        inc_data['Inc'] = main.flatten(inc)
        inc_data['Site'] = site
        exc_data['Exc'] = main.flatten(exc)
        exc_data['Site'] = site
        if IP in inc_data['Inc']:
            if IP not in exc_data['Exc']:
                output[IP] = inc_data['Site']

        
        with open(f'Output\\Site_Finder({date_str}).txt', 'a') as output_f: # Creating file handler for the .txt output file
            output_f.write(f"{str(output)}\n") # Writing output to the .txt file (line by line)
            
    print(f'\nThe result is: {output}') # Prints the IP and its associated Site's name
    end = timer() # To time how long the code takes to run
    print(f"\nCode execution complete, time elapsed: {round((end-start)/60)} minute(s)")

if IP == None: # User chose to look-up several IP addresses
    start = timer() # To time how long the code takes to run
    print("\n------------------------------------------\nResults:\n")
    now = datetime.now() # Getting today's date & time
    date_str = now.strftime("%m-%d-%Y_T%H-%M-%S") # Creating date-time string
    IPs = open(f'{IPs_path}', 'r') # Reading the IP addresses in the user provided file
    contents = IPs.read()
    lines = contents.split('\n') # Converting the txt file contents to a Python list
    for line in lines: # Reading each IP in the provided IP list
        IP = line
        info = main.site_targets.copy() # Making a copy of the site targets api call dataframe
        info = info[['Site Name', 'Included Targets', 'Excluded Targets']] # Filtering the dataframe for needed columns

        inc_data = {  
            'Inc':None,
            'Site':None
        }
        exc_data = {
            'Exc':None,
            'Site':None
        }
        output = {}
        inc_list = []
        exc_list = []

        for inc, exc, site in zip(info['Included Targets'], info['Excluded Targets'], info['Site Name']):
            inc_data['Inc'] = main.flatten(inc)
            inc_data['Site'] = site
            exc_data['Exc'] = main.flatten(exc)
            exc_data['Site'] = site
            if IP in inc_data['Inc']:
                if IP not in exc_data['Exc']:
                    output[IP] = inc_data['Site']

        print(output) # Prints the IP and its associated Site's name
        with open(f'Output\\Site_Finder({date_str}).txt', 'a') as output_f: # Creating file handler for the .txt output file
            output_f.write(f"{str(output)}\n") # Writing output to the .txt file (line by line)

    end = timer() # To time how long the code takes to run
    print(f"\nCode execution complete, time elapsed: {round((end-start)/60)} minute(s)")