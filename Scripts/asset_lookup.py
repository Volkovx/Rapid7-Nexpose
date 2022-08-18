'''
This script provides info on any asset in Nexpose DB using the asset's hostname, IP, or ID.

__author__ = xVolkov
__github__ = https://github.com/xVolkov
__date__ = 08/18/2022
__version__ = "1.0"

'''

import pandas as pd
import numpy as np
import csv
import os
import sys

def drop_domain(in_name):
    '''
        > Function: removes domain names and/or any strings after '.'
    '''
    try:
        out_name = in_name.split('.')[0]
    except:
        out_name = in_name
    return out_name

# USE THIS FILE TO LOOKUP ASSETS IN NEXPOSE
assets = pd.read_csv('C:/Data/All_Assets_Scanned.csv')  # Change to match your all assets file

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
                       "2) Search by hostname\n3) Search by asset ID\n")

    if search == '1': # user is searching by asset IP address
        asset_ip = input("Please enter the asset's IP address: ")
        while not asset_ip:
            print("Invalid input!")
            asset_ip = input("Please enter the asset's IP address: ")
        found_ip = assets[assets.ip_address_all.str.contains(asset_ip)] # stores assets matched using provided IP
        print('\n',found_ip)
        
    elif search == '2': # user is searching by asset hostname
        asset_hostname = input("Please enter the asset's hostname: ")
        while not asset_hostname:
            print("Invalid input!")
            asset_hostname = input("Please enter the asset's hostname: ")
        asset_hostname = asset_hostname.lower() # Lower-cases the user input
        asset_hostname = drop_domain(asset_hostname) # Applies drop_domain function on the user input
        found_hostname = assets[assets.host_name.str.contains(asset_hostname, na=False)] # stores assets matched using provided hostname
        print('\n',found_hostname)
        
    elif search == '3': # user is searching by asset ID
        asset_id = input("Please enter the asset's ID: ")
        while not asset_id:
            print("Invalid input!")
            asset_id = input("Please enter the asset's ID: ")
        found_id = assets.loc[assets['asset_id'] == int(asset_id)] # stores assets matched using provided asset ID
        if 'Empty DataFrame' in str(found_id):
            print("\nAsset not found! Please check your input..")
        else:
            print('\n',found_id)
        
    elif search =='0': # user chose to exit the program
        print("Exiting program..")
        sys.exit()