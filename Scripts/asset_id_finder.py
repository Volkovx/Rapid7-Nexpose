'''
This script takes a .txt file containing either hostnames OR IPs as an input (each entry must be separated by a newline),
then outputs the asset ID and a short summary on the asset.

__author__ = "xVolkov"
__github__ = https://github.com/xVolkov
__date__ = "08/16/2022"
__version__ = "1.0"


'''

import pandas as pd
import numpy as np
import csv
import os
import sys
import datetime
from datetime import datetime, timedelta, date
from time import strftime

def drop_domain(in_name):
    '''
        > Function: removes domain names and/or any strings after a '.' (dot)
    '''
    try:
        out_name = in_name.split('.')[0]
    except:
        out_name = in_name
    return out_name

# USE THIS FILE TO LOOKUP ASSETS IN NEXPOSE
assets = pd.read_csv('C:/Data/All_Assets.csv') # Change to match your all assets file

# Filtering 'assets' dataframe:
assets['host_name'] = assets['host_name'].apply(drop_domain) # dropping domains on 'host_name' column
assets = assets.sort_values('host_name', ascending=True) # sorting 'host_name' column
assets['host_name'] = assets['host_name'].str.lower() # lower-casing all data in 'host_name' column
assets['ip_address_all'] = assets['ip_address_all'].apply(lambda x: x.split(', ')) # splits multiple IPs in 'ip_address_all'
assets = assets.explode('ip_address_all') # assigns each IP to its own row
print('assets size: ',assets.shape[0])

x = 1
while x == 1:
    search = input("\n############################################################\n"+
                   "Please select one of the following options ('0' to exit):\n1) Search by IP address\n" +
                       "2) Search by hostname\n")
    
    if search == '1': # user is searching by asset IP address
        ip_file = input("Please enter file path to your .txt file containing "+
                         "all asset IP addresses (have each IP seaparated by a newline): \n")
        if (os.path.isfile(ip_file)) == True:
            
            if ip_file.endswith('.txt'):
                output = pd.DataFrame() # Empty dataframe which will contain all results
                print('\nFile found! Getting results..')
                file = open(ip_file)
                file_content = file.read() # Reads the contents of the input file
                lines = file_content.split('\n') # Splits entries using the newline character as a delimiter
                for line in lines:
                    IP = line
                    DB = assets.copy()
                    DB = DB[['asset_id','host_name','ip_address_all','vulnerabilities','Operating System',
                             'Last Scan Date','Site ID', 'Authentication']]

                    data = pd.DataFrame() # Contains search results

                    for entry in DB['ip_address_all']:
                        if IP == entry:
                            data = data.append(DB[DB.ip_address_all.str.contains(IP)])
                    
                    now = datetime.now() # Getting today's date & time
                    date_str = now.strftime("%m-%d-%Y_T%H-%M-%S") # Creating date-time string
                    output = output.append(data)
                    
                output.to_csv(f'Output/Asset IDs/{date_str}.csv', index=False) # Saving results
                print("All done! Results were saved to '/Output/Asset IDs'")
                    
            else:
                print("\nInvalid input! File is not a .txt!")
                
        else:
            print("\nInvalid input! File Does not exist!")
            

    elif search == '2': # user is searching by asset hostname
        hn_file = input("Please enter file path to your .txt file containing "+
                         "all asset hostnames (have each hostname seaparated by a newline): \n")

        if (os.path.isfile(hn_file)) == True: # checks if file exists
            if ip_file.endswith('.txt'): # check if file type is .txt
                print('\nFile found! Getting results..')
                output = pd.DataFrame() # empty dataframe which will contain all results
                file = open(hn_file) # opens the hostnames file
                file_content = file.read() # Reads the contents of the input file
                lines = file_content.split('\n') # Splits entries using the newline character as a delimiter
                for line in lines: # goes through each hostname in the hn_file
                    hostname = line
                    hostname = hostname.lower() # lower-cases each hostname in the file
                    hostname = drop_domain(hostname) # applies drop_domain function on the hostname
                    DB = assets.copy() # creates a copy of the all_assets.csv file above (assets)
                    DB = DB[['asset_id','host_name','ip_address_all','vulnerabilities','Operating System',
                             'Last Scan Date','Site ID', 'Authentication']] # choosing specific column to filter for from the all_assets file

                    data = pd.DataFrame() # Contains search results (output)
                    data = data.append(DB[DB.host_name.str.contains(hostname, na=False)]) # queries the user provided hostname through the all_assets file's 'host_name' column
                    
                    now = datetime.now() # gets today's date & time
                    date_str = now.strftime("%m-%d-%Y_T%H-%M-%S") # creating date-time string
                    output = output.append(data) # appends info from 'data' into 'output' at each for-loop iteration
                    
                output.to_csv(f'Output/Asset IDs/{date_str}.csv', index=False) # Saving results to 'Output' directory
                print("All done! Results were saved to '/Output/Asset IDs'")
                
            else:
                print("\nInvalid input! File is not a .txt!")
                
        else:
            print("\nInvalid input! File Does not exist!")
        
    elif search =='0': # user chose to exit the program
        print("Exiting program..")
        sys.exit()
        

