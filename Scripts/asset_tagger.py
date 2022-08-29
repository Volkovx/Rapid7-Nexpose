'''
This script provides info on any asset in Nexpose DB using the asset's hostname, IP, or ID.

__author__ = xVolkov
__github__ = https://github.com/xVolkov
__date__ = 08/29/2022
__version__ = "1.0"

'''

import os
import csv
import json
import sys
from timeit import default_timer as timer
import netaddr
import ipaddress
from datetime import datetime, timedelta, date
import numpy as np
import pandas as pd
from io import StringIO
from io import BytesIO
from pathlib import Path
from getpass import getpass
from base64 import b64encode as b64e
from base64 import b64decode as b64d
from time import strftime
import urllib3
import requests
from tqdm import tqdm
from requests.packages.urllib3.exceptions import InsecureRequestWarning


requests.packages.urllib3.disable_warnings(InsecureRequestWarning) # Disable cert warnings

class Main:
    def __init__(self, host=None, auth=None, tag_name=None):
        '''
            > Function: python class constructor, includes all class attributes
        '''
        self.auth = auth # Stores encoded user credentials.
        self.host = host # Stores chosen host URL.
        self.tag_name = tag_name
        
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
        else:
            self.auth = auth 
            
        self.test_connection()
            
    def get_auth(self):
        ''' 
        > Fucntion: Gets user's credentials (username and pass).
        '''
        return (self.auth[0],b64d(self.auth[1]).decode())
   
    def test_connection(self): 
        '''
            > Function: tests user connection to chosen host
        '''
        url = f"{self.host}/sites"
        response = requests.get(url, auth=(self.auth[0],b64d(self.auth[1]).decode()), params={'page':0, 'size':1},
                                verify=False)
        try:
            response.raise_for_status()
        except:
            print(f'Unable to query API. Request returned error - {response.status_code}: {response.json()["message"]}')
            
    def get_tags(self):
        '''
            > Function: gets all tags in Nexpose
        '''
        response = requests.get(self.host + f"/tags", auth=self.get_auth(), params={'size': 500}, verify=False)
        return response.json()['resources']
    
    def get_tag_id(self, tag_name): 
        '''
            > Function: gets specified tag ID by looking-up the tag's name
        '''
        tag_name = tag_name
        tag_dict = {}
        for tag in self.get_tags(): # Looks-up tag id by its name
            if tag['name'] == f'{tag_name}':
                tag_dict.update({tag['name']:tag['id']})
        print("This function returns a Python dict in '{Tag name : Tag ID}' format..")
        return tag_dict

    def get_tagged_assets(self, tag_id):
        response = requests.get(self.host + f"/tags/{tag_id}/assets", auth=self.get_auth(),
                                    params={'size' : 500}, verify=False)
        return (response.json())


##### Code Runner ####

asset_id = None
tag_id = None
tag_name = None

main = Main()
x = 1
while x == 1:
    id_file = input("\nPlease enter file path to your .txt file including "+
                         "all asset IDs you'd like to tag (have each ID seaparated by a newline): \n")
    search = input("\n############################################################\n"+
                   "Please select one of the following options ('0' to exit):\n1) Tag assets using a tag ID\n" +
                       "2) Tag assets using a tag name\n" + "3) Untag assets using a tag ID\n" +
                       "4) Untag assets using a tag name\n")

    if search == '1': # OPTION 1) TAG ASSETS USING TAG ID
        tag_id = input("Please enter the tag id: \n") #Stores tag id used to tag the asset
        tag_id = int(tag_id)
        if (os.path.isfile(id_file)) == True:

            if id_file.endswith('.txt'):
                output = pd.DataFrame() # Empty dataframe which will contain all results
                print('\nFile found! Processing data.. \n')
                file = open(id_file)
                file_content = file.read() # Reads the contents of the input file
                lines = file_content.split('\n') # Splits entries using the newline character as a delimiter
                log = [] # List storing asset IDs and their tags
                    
                response = requests.get(main.host + f"/tags", auth=main.get_auth(), params={'size': 500}, verify=False)
                all_tags = response.json()['resources']
                if response.json()['page']['totalPages'] > 1:
                    for page in range(1,response.json()['page']['totalPages']):
                        response = requests.get(url, auth=self.get_auth(), params={'page':page, 'size':500}, verify=False)
                        response.raise_for_status()
                        all_tags = all_tags + response.json()['resources']

                for tag in all_tags: # Looks-up tag id by its name
                    if tag['id'] == tag_id:
                        print('Tag found! \n')
                        print(f"Tag Name: {tag['name']}")
                        print(f"Tag ID: {tag['id']} \n")
                        tag_id = tag['id']
                        
                        proceed = input(f"Would you like to tag your assets with tag {tag_id} (y/n)?\n")
                
                for asset_id in lines:
                    if 'y' in proceed:
                        pass
                    elif 'n' in proceed:
                        print("Exiting program..")
                        sys.exit()
                    else:
                        print("Exiting program..")
                        sys.exit()
                        
                    if tag_id == None:
                        print("Tag not found! Exiting program..")
                        sys.exit()
                    else:
                        response = requests.put(main.host + f"/assets/{asset_id}/tags/{tag_id}", auth=main.get_auth(),
                                                verify=False)
                        log.append(f"Asset ID {asset_id} successfully tagged with tag {tag_id}\n")  
                        print('\n')
                        print(response.json())
                        print('\n')

                now = datetime.now()
                date_str = now.strftime("%m-%d-%Y_T%H-%M-%S") # Gets date and time
                log_output = f'Output/AssetsTagged_Log({date_str}).txt' # Log output file destination
                try: # Saving log as a .txt file
                    with open(log_output, 'w') as f:
                        f.write('Assets Tagged Summary:\n\n')
                        for item in log:
                            f.write("%s\n" % item)
                except IOError:
                    print('I/O error')

                #output.to_csv(f'Output/Asset IDs/{date_str}.csv', index=False) # Saving results
                print("All done! Results were saved to 'Output' directory")

            else:
                print("\nInvalid input! File is not a .txt!")

        else:
            print("\nInvalid input! File Does not exist!")


    elif search == '2': # OPTION 2) TAG ASSETS USING TAG NAME 
        tag_name = input("Please enter the tag name: \n") #Stores tag id used to tag the asset
        
        if (os.path.isfile(id_file)) == True:

            if id_file.endswith('.txt'):
                output = pd.DataFrame() # Empty dataframe which will contain all results
                print('\nFile found! Processing data.. \n')
                file = open(id_file)
                file_content = file.read() # Reads the contents of the input file
                lines = file_content.split('\n') # Splits entries using the newline character as a delimiter
                log = [] # List storing asset IDs and their tags

                response = requests.get(main.host + f"/tags", auth=main.get_auth(), params={'size': 500}, verify=False)
                all_tags = response.json()['resources']
                if response.json()['page']['totalPages'] > 1:
                    for page in range(1,response.json()['page']['totalPages']):
                        response = requests.get(url, auth=self.get_auth(), params={'page':page, 'size':500}, verify=False)
                        response.raise_for_status()
                        all_tags = all_tags + response.json()['resources']

                for tag in all_tags: # Looks-up tag id by its name
                    if tag['name'] == f'{tag_name}':
                        print('Tag found! \n')
                        print(f"Tag Name: {tag['name']}")
                        print(f"Tag ID: {tag['id']} \n")
                        tag_id = tag['id']
                        
                        proceed = input(f"Would you like to tag your assets with tag {tag_id} (y/n)?\n")
                
                for asset_id in lines:
                    if 'y' in proceed:
                        pass
                    elif 'n' in proceed:
                        print("Exiting program..")
                        sys.exit()
                    else:
                        print("Exiting program..")
                        sys.exit()
                        
                    if tag_id == None:
                        print("Tag not found! Exiting program..")
                        sys.exit()
                    else:
                        response = requests.put(main.host + f"/assets/{asset_id}/tags/{tag_id}", auth=main.get_auth(),
                                                verify=False)
                        log.append(f"Asset ID {asset_id} successfully tagged with tag {tag_id}\n")  
                        print('\n')
                        print(response.json())
                        print('\n')

                now = datetime.now()
                date_str = now.strftime("%m-%d-%Y_T%H-%M-%S") # Gets date and time
                log_output = f'Output/AssetsTagged_Log({date_str}).txt' # Log output file destination
                try: # Saving log as a .txt file
                    with open(log_output, 'w') as f:
                        f.write('Assets Tagged Summary:\n\n')
                        for item in log:
                            f.write("%s\n" % item)
                except IOError:
                    print('I/O error')

                #output.to_csv(f'Output/Asset IDs/{date_str}.csv', index=False) # Saving results
                print("All done! Results were saved to 'Output' directory")

            else:
                print("\nInvalid input! File is not a .txt!")

        else:
            print("\nInvalid input! File Does not exist!")
    
    
    elif search =='3': # OPTION 3) UNTAG ASSETS USING TAG ID
        tag_id = input("Please enter the tag id: \n") #Stores tag id used to tag the asset
        tag_id = int(tag_id)
        if (os.path.isfile(id_file)) == True:

            if id_file.endswith('.txt'):
                output = pd.DataFrame() # Empty dataframe which will contain all results
                print('\nFile found! Processing data.. \n')
                file = open(id_file)
                file_content = file.read() # Reads the contents of the input file
                lines = file_content.split('\n') # Splits entries using the newline character as a delimiter
                log = [] # List storing asset IDs and their tags
                    
                response = requests.get(main.host + f"/tags", auth=main.get_auth(), params={'size': 500}, verify=False)
                all_tags = response.json()['resources']
                if response.json()['page']['totalPages'] > 1:
                    for page in range(1,response.json()['page']['totalPages']):
                        response = requests.get(url, auth=self.get_auth(), params={'page':page, 'size':500}, verify=False)
                        response.raise_for_status()
                        all_tags = all_tags + response.json()['resources']

                for tag in all_tags: # Looks-up tag id by its name
                    if tag['id'] == tag_id:
                        print('Tag found! \n')
                        print(f"Tag Name: {tag['name']}")
                        print(f"Tag ID: {tag['id']} \n")
                        tag_id = tag['id']
                        
                        proceed = input(f"Would you like to remove tag {tag_id} from your assets (y/n)?\n")
                
                for asset_id in lines:
                    if 'y' in proceed:
                        pass
                    elif 'n' in proceed:
                        print("Exiting program..")
                        sys.exit()
                    else:
                        print("Exiting program..")
                        sys.exit()
                        
                    if tag_id == None:
                        print("Tag not found! Exiting program..")
                        sys.exit()
                    else:
                        response = requests.delete(main.host + f"/assets/{asset_id}/tags/{tag_id}", auth=main.get_auth(),
                                                verify=False)
                        log.append(f"Tag {tag_id} successfully removed from asset {asset_id}\n")  
                        print('\n')
                        print(response.json())
                        print('\n')

                now = datetime.now()
                date_str = now.strftime("%m-%d-%Y_T%H-%M-%S") # Gets date and time
                log_output = f'Output/AssetsTagged_Log({date_str}).txt' # Log output file destination
                try: # Saving log as a .txt file
                    with open(log_output, 'w') as f:
                        f.write('Assets Untagged Summary:\n\n')
                        for item in log:
                            f.write("%s\n" % item)
                except IOError:
                    print('I/O error')

                #output.to_csv(f'Output/Asset IDs/{date_str}.csv', index=False) # Saving results
                print("All done! Results were saved to 'Output' directory")

            else:
                print("\nInvalid input! File is not a .txt!")

        else:
            print("\nInvalid input! File Does not exist!")
            
    
    elif search == '4': # OPTION 4) UNTAG ASSETS USING TAG NAME
        tag_name = input("Please enter the tag name: \n") #Stores tag id used to tag the asset
        
        if (os.path.isfile(id_file)) == True:

            if id_file.endswith('.txt'):
                output = pd.DataFrame() # Empty dataframe which will contain all results
                print('\nFile found! Processing data.. \n')
                file = open(id_file)
                file_content = file.read() # Reads the contents of the input file
                lines = file_content.split('\n') # Splits entries using the newline character as a delimiter
                log = [] # List storing asset IDs and their tags

                response = requests.get(main.host + f"/tags", auth=main.get_auth(), params={'size': 500}, verify=False)
                all_tags = response.json()['resources']
                if response.json()['page']['totalPages'] > 1:
                    for page in range(1,response.json()['page']['totalPages']):
                        response = requests.get(url, auth=self.get_auth(), params={'page':page, 'size':500}, verify=False)
                        response.raise_for_status()
                        all_tags = all_tags + response.json()['resources']

                for tag in all_tags: # Looks-up tag id by its name
                    if tag['name'] == f'{tag_name}':
                        print('Tag found! \n')
                        print(f"Tag Name: {tag['name']}")
                        print(f"Tag ID: {tag['id']} \n")
                        tag_id = tag['id']
                        
                        proceed = input(f"Would you like to remove tag {tag_id} from your assets (y/n)?\n")
                
                for asset_id in lines:
                    if 'y' in proceed:
                        pass
                    elif 'n' in proceed:
                        print("Exiting program..")
                        sys.exit()
                    else:
                        print("Exiting program..")
                        sys.exit()
                        
                    if tag_id == None:
                        print("Tag not found! Exiting program..")
                        sys.exit()
                    else:
                        response = requests.delete(main.host + f"/assets/{asset_id}/tags/{tag_id}", auth=main.get_auth(),
                                                verify=False)
                        log.append(f"Tag {tag_id} successfully removed from asset {asset_id}\n")  
                        print('\n')
                        print(response.json())
                        print('\n')

                now = datetime.now()
                date_str = now.strftime("%m-%d-%Y_T%H-%M-%S") # Gets date and time
                log_output = f'Output/AssetsTagged_Log({date_str}).txt' # Log output file destination
                try: # Saving log as a .txt file
                    with open(log_output, 'w') as f:
                        f.write('Assets Tagged Summary:\n\n')
                        for item in log:
                            f.write("%s\n" % item)
                except IOError:
                    print('I/O error')

                #output.to_csv(f'Output/Asset IDs/{date_str}.csv', index=False) # Saving results
                print("All done! Results were saved to 'Output' directory")

            else:
                print("\nInvalid input! File is not a .txt!")

        else:
            print("\nInvalid input! File Does not exist!")


    elif search =='0':
        print("Exiting program..")
        sys.exit()
