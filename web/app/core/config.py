import os

from dotenv import load_dotenv


load_dotenv()


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
    BACKEND_URL = os.getenv('BACKEND_URL', 'http://backend:8000')
    DEBUG = os.getenv('DEBUG', 'True') == 'True'

