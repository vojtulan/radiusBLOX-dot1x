import requests
import json
import mysql.connector
import argparse
from datetime import datetime

log = "log.txt"
branch = "branch"

dbUsername ='radius'
dbPassword ='password'
dbHost ='localhost'
dbName ='radius'

infobloxUrl="infoblox.domain.io"
apiCallTimeout = 5

apiUsername = "apiusername"
apiKey = "apikey"

class ApiRecord:
  def __init__(self, hostName, macAddress, vlan, location):
    self.hostName = hostName
    self.macAddress = macAddress
    self.vlan = vlan
    self.location = location

class DbRecord:
  def __init__(self, dbId, macAddress, vlan):
    self.dbId = dbId
    self.macAddress = macAddress
    self.vlan = vlan


def LogErrorToFile(error):
    time = str(datetime.now())
    with open(log, 'a') as logfile:
        logfile.write(time + ": " + error + '\n')

def GetApiRecord() -> ApiRecord:

    print("Getting data from Infoblox API ... ")
    requests.packages.urllib3.disable_warnings()  # Disable SSL warnings in requests #
    url = f'https://{infobloxUrl}/wapi/v2.11/record:host?_return_fields%2B=extattrs&*Lokalita={branch}'

    try:
        response = requests.request("GET", url, auth=(apiUsername, apiKey), verify=False, timeout=apiCallTimeout )
        jsonData = json.loads(response.text)

    except requests.exceptions.HTTPError as error:
        LogErrorToFile(str(error))
        exit()

    except requests.exceptions.ConnectionError as error:
        LogErrorToFile(str(error))
        exit()
        
    except requests.exceptions.Timeout as error:
        LogErrorToFile(str(error))
        exit()

    except requests.exceptions.RequestException as error:
        LogErrorToFile(str(error))
        exit()
        
    except:
        LogErrorToFile("Failed to establish connection with API. Quitting ...")
        exit()


    if not jsonData:
        LogErrorToFile("Response is an empty array.")

    apiRecords = []

    for object in jsonData:
        hostName = object['name']
        location = object['extattrs']['Lokalita']['value']
        macAddress = object['ipv4addrs'][0]['mac'].replace(":", "").lower()
        vlan = object['extattrs']['VLAN']['value']
        if not vlan:
            continue
        apiRecords.append(ApiRecord(hostName, macAddress, vlan, location))

    return apiRecords

def GetDbRecords() -> DbRecord:
    try:
        connection = mysql.connector.connect(host=dbHost, database=dbName, user=dbUsername, password=dbPassword)
        sql_select_Query = "select * from radusergroup"
        cursor = connection.cursor()
        cursor.execute(sql_select_Query)
        # get all records
        dbRows = cursor.fetchall()
        
        dbRecords = []

        for dbRow in dbRows:
            dbId = dbRow[0]
            username = dbRow[1]
            vlan = str(dbRow[2])[4:]
            dbRecords.append(DbRecord(dbId, username, vlan))

        if connection.is_connected():
            connection.close()
            cursor.close()
            
        return dbRecords
            
    except mysql.connector.Error as e:
        LogErrorToFile("Error reading data from MySQL table - " + e.msg)
        exit()

def GetAllVlans():
    try:
        connection = mysql.connector.connect(host=dbHost, database=dbName, user=dbUsername, password=dbPassword)
        sql_select_Query = 'select value from radgroupreply where attribute = "Tunnel-Private-Group-Id"'
        cursor = connection.cursor()
        cursor.execute(sql_select_Query)
        # get all records
        dbRows = cursor.fetchall()
        
        vlanList = []

        for dbRow in dbRows:
            vlanList.append(dbRow[0])

        if connection.is_connected():
            connection.close()
            cursor.close()
            
        return vlanList
            
    except mysql.connector.Error as e:
        LogErrorToFile("Error reading data from MySQL table - " + e.msg)
        exit()

def ExecuteSqlQuerries(querries):
    try:
        connection = mysql.connector.connect(host=dbHost, database=dbName, user=dbUsername, password=dbPassword)
        cursor = connection.cursor()
        for querry in querries:
            cursor.execute(querry)

        connection.commit()

        if connection.is_connected():
            cursor.close()
            connection.close()

    except mysql.connector.Error as error:
        LogErrorToFile("Failed to execute MySQL querries. {}".format(error))
        exit()

def FindDbRecordById(dbRecords, dbId):
    for dbRecord in dbRecords:
        if dbRecord.dbId == dbId:
            return dbRecord

    return None

def FindDbRecordByMacAddress(dbRecords, macAddress):
    for dbRecord in dbRecords:
        if  macAddress == dbRecord.macAddress:
            return dbRecord

    return None

apiRecords = GetApiRecord()
dbRecords = GetDbRecords()
sqlQuerriesToExexute = []

#Testing
#apiRecords.pop(0)

for dbRecord in dbRecords:
    recordExistsInApi = False

    for apiRecord in apiRecords:

        if (dbRecord.macAddress == apiRecord.macAddress):
            recordExistsInApi = True
            break
    
    if not recordExistsInApi:
        sqlQuerriesToExexute.append(f'DELETE FROM radcheck WHERE id = {dbRecord.dbId}')
        sqlQuerriesToExexute.append(f'DELETE FROM radusergroup WHERE id = {dbRecord.dbId}')

dbRecords = GetDbRecords()

ExecuteSqlQuerries(sqlQuerriesToExexute)
sqlQuerriesToExexute = []

vlanList = GetAllVlans()
for apiRecord in apiRecords:
    if not apiRecord.vlan in vlanList:
        sqlQuerriesToExexute
        sqlQuerriesToExexute.append(f'insert into radgroupreply (groupname, attribute, op, value) values ("VLAN{apiRecord.vlan}", "Tunnel-Type", "=", "13")')
        sqlQuerriesToExexute.append(f'insert into radgroupreply (groupname, attribute, op, value) values ("VLAN{apiRecord.vlan}", "Tunnel-Medium-Type", "=", "6")')
        sqlQuerriesToExexute.append(f'insert into radgroupreply (groupname, attribute, op, value) values ("VLAN{apiRecord.vlan}", "Tunnel-Private-Group-Id", "=", "{apiRecord.vlan}")')
        vlanList.append(apiRecord.vlan)

potentiallyAvailableId = 1

for apiRecord in apiRecords:
    
    existingDbRecordByMacAddress = FindDbRecordByMacAddress(dbRecords, apiRecord.macAddress)

    if existingDbRecordByMacAddress == None:
        
        existingDbRecordById = FindDbRecordById(dbRecords, potentiallyAvailableId)

        while existingDbRecordById != None:
            potentiallyAvailableId += 1
            existingDbRecordById = FindDbRecordById(dbRecords, potentiallyAvailableId)

        sqlQuerriesToExexute.append(f'INSERT INTO radcheck (id, username, attribute, op, value) VALUES ({potentiallyAvailableId}, "{apiRecord.macAddress}", "Cleartext-Password", ":=", "{apiRecord.macAddress}")')
        sqlQuerriesToExexute.append(f'INSERT INTO radusergroup (id, username, groupname, priority) VALUES ({potentiallyAvailableId}, "{apiRecord.macAddress}", "VLAN{apiRecord.vlan}", "10")')

        potentiallyAvailableId += 1

    elif apiRecord.vlan != existingDbRecordByMacAddress.vlan:
        sqlQuerriesToExexute.append(f'UPDATE radusergroup SET priority = {apiRecord.vlan} WHERE id = {existingDbRecordByMacAddress.dbId}')


ExecuteSqlQuerries(sqlQuerriesToExexute)
exit()