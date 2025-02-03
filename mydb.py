import mysql.connector
dataBase = mysql.connector.connect( 
    host = 'localhost',
    user = 'root',
    password = 'Revathi12',
)
cursorObject = dataBase.cursor()
cursorObject.execute("CREATE DATABASE eldernew")
print("All Done.")
