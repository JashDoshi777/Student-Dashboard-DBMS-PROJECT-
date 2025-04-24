# config.py
import os

class Config:

    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY') or 'some_random_secret_key'


    DB_HOST = 'localhost'
    DB_USER = 'root'                
    DB_PASSWORD = 'Jashdoshi7$'  
    DB_NAME = 'student_portal'     
