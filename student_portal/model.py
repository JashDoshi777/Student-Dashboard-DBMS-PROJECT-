
from flask import Flask
import mysql.connector

app = Flask(__name__)

def get_db_connection():
    connection = mysql.connector.connect(
        host="localhost",
        user="root",
        password="Jashdoshi7$",
        database="student_portal"
    )
    return connection
