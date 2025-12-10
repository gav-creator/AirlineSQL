import mysql.connector
from mysql.connector import Error

def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="root",
            database="airline_management"
        )
        return conn
    except Error as e:
        print("Database connection error:", e)
        return None
