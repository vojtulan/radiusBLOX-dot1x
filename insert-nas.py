import mysql.connector
import csv

log = "log.txt"

dbUsername ='root'
dbPassword ='Hu@wei123'
dbHost ='10.40.0.252'
dbName ='radius'
secret = "testing123"


sqlQuerriesToExexute = ["truncate nas"]

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
        print(error)
        
        
with open('nas.txt') as csv_file:
    csv_reader = csv.reader(csv_file, delimiter=';')
    for row in csv_reader:
        ip = row[2]
        name = row[1]
        location = row[0]
        newQuerry = f' INSERT INTO nas VALUES (NULL ,  "{ip}",  "{name}",  "other", NULL ,  "{secret}" , NULL , NULL ,  "{location}");'
        sqlQuerriesToExexute.append(newQuerry)
        
ExecuteSqlQuerries(sqlQuerriesToExexute)
        