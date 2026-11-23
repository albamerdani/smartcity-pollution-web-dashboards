import os
from pathlib import Path
from dotenv import load_dotenv
BASE_DIR=Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR/'.env')
SECRET_KEY=os.environ.get('DJANGO_SECRET_KEY','unsafe-development-only')
DEBUG=os.environ.get('DJANGO_DEBUG','false').lower()=='true'
ALLOWED_HOSTS=[s.strip() for s in os.getenv('DJANGO_ALLOWED_HOSTS','localhost,127.0.0.1').split(',') if s.strip()]
INSTALLED_APPS=['django.contrib.auth','django.contrib.contenttypes','monitoring']
MIDDLEWARE=['django.middleware.security.SecurityMiddleware','django.middleware.common.CommonMiddleware']
ROOT_URLCONF='config.urls'
TEMPLATES=[]
WSGI_APPLICATION='config.wsgi.application'
DATABASES={'default':{'ENGINE':'django.db.backends.postgresql','NAME':os.getenv('DB_NAME','smartcity'),
'USER':os.getenv('DB_USER','smartcity_api'),'PASSWORD':os.getenv('DB_PASSWORD',''),
'HOST':os.getenv('DB_HOST','localhost'),'PORT':os.getenv('DB_PORT','5432'),
'OPTIONS':{'sslmode':os.getenv('DB_SSLMODE','prefer')}}}
LANGUAGE_CODE='en-us'
TIME_ZONE='UTC'
USE_TZ=True
DEFAULT_AUTO_FIELD='django.db.models.BigAutoField'
SECURE_CONTENT_TYPE_NOSNIFF=True
