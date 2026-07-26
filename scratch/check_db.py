import pymysql

try:
    connection = pymysql.connect(
        host="107.172.193.34",
        user="root",
        password="root2020",
        database="dulce_espera",
        port=3306,
        connect_timeout=5
    )
    print("Connection direct to MySQL SUCCESSFUL!")
    connection.close()
except Exception as e:
    print(f"Direct connection failed: {e}")
