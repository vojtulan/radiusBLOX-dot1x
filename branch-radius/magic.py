import requests
import json
from mysql.connector import connect, Error
import mysql.connector
import argparse
from datetime import datetime
import pprint

log = "log.txt"
macAdresses = []


def GetDataFromInfoblox():  
    print("Getting data from Infoblox API ... ")
    requests.packages.urllib3.disable_warnings()  # Disable SSL warnings in requests #
    url = "https://infoblox.altepro.cz/wapi/v2.11/record:host?_return_fields%2B=extattrs&*Lokalita=PCE"
    try:
        response = requests.request("GET", url, auth=('api', 'api123'), verify=False)
        jsonData = json.loads(response.text)

    except:
        time = str(datetime.now())
        error = ": Failed to establish connection with API. Quitting ..."
        print(error)
        with open(log, 'a') as logfile:
            logfile.write(time + error + '\n')
            exit()

    if not jsonData:
        time = str(datetime.now())
        error = ": Response is an empty array. Quitting ..."
        print(error)
        with open(log, 'a') as logfile:
            logfile.write(time + error + '\n')
            exit()
    else:
        return jsonData

def CheckIfDbRunning():
    try:
        with connect(host="10.40.0.253",user="root",password="Hu@wei123") as connection:
            print("DB is OK ...")
    except Error as e:
        print("ERROR: ", e)
        e = str(e)
        time = str(datetime.now())
        with open(log, 'a') as logfile:
            logfile.write(time + e + '\n')
        exit()


def InsertIntoDB(username, attribute, op, value, groupname, priority):          
    radcheckInsertQuerry = """INSERT INTO radcheck (username, attribute, op, value) VALUES (%s, %s, %s, %s)"""
    radUserGroupQuerry = """INSERT INTO radusergroup (username, groupname, priority) VALUES (%s, %s, %s) """
    radcheckRecord = (username, attribute, op, value)
    radUserGroupRecord = (username, groupname, priority)
    cursor.execute(radcheckInsertQuerry, radcheckRecord)
    cursor.execute(radUserGroupQuerry, radUserGroupRecord)
    connection.commit()
    print("Record inserted successfully into radius DB")

def TruncateDB():
    truncateQuerry = "TRUNCATE radcheck;"
    truncateQuerry2 = "TRUNCATE radusergroup"
    cursor.execute(truncateQuerry)
    cursor.execute(truncateQuerry2)
    connection.commit()
    print("DB has been successfully truncated")

def CheckDupes(list):
    dup = [x for i, x in enumerate(list) if i != list.index(x)]
    return dup


CheckIfDbRunning()
dataFromInfoblox = GetDataFromInfoblox()

try:
    connection = mysql.connector.connect(user='root', password='Hu@wei123',host='10.40.0.253',database='radius')
    cursor = connection.cursor()
    TruncateDB()

    for object in dataFromInfoblox:
        hostName = object['name']
        location = object['extattrs']['Lokalita']['value']
        unformatedMacAddress = object['ipv4addrs'][0]['mac']
        vlan = object['extattrs']['VLAN']['value']
        macAddress = unformatedMacAddress.replace(":", "").lower()
        macAdresses.append(macAddress)
        InsertIntoDB(macAddress, 'Cleartext-Password', ":=", macAddress,'VLAN#', vlan)
    
    cursor.close()
    connection.close()

    macAdresses.append("000000000008")
    macAdresses.append("000000000000")

    if CheckDupes(macAdresses):
        print("DUPE ITEMS in Infoblox !")
        e = " DUPLICATE Items from Infoblox - "
        strDupes = ""
        dupes = (CheckDupes(macAdresses))
        for dupe in dupes: 
            strDupes += dupe + ", "
        strDupes = strDupes[:-2]
        time = str(datetime.now())
        with open(log, 'a') as logfile:
            logfile.write(time + str(e) + str(strDupes) + '\n')
            print((time + str(e) + str(strDupes) + '\n'))
        exit()

except mysql.connector.Error as error:
    print("Failed to connect into DB. Quitting ...")
    time = str(datetime.now())
    with open(log, 'a') as logfile:
        logfile.write(time + str(error) + '\n')
    exit()