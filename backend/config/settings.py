import os
from pathlib import Path
from datetime import timedelta
BASE_DIR=Path(__file__).resolve().parent.parent
SECRET_KEY=os.getenv('DJANGO_SECRET_KEY','development-only-change-me')
DEBUG=os.getenv('DJANGO_DEBUG','false').lower()=='true'
ALLOWED_HOSTS=[v.strip() for v in os.getenv('DJANGO_ALLOWED_HOSTS','localhost,127.0.0.1,api').split(',') if v.strip()]
INSTALLED_APPS=['django.contrib.admin','django.contrib.auth','django.contrib.contenttypes','django.contrib.sessions','django.contrib.messages','django.contrib.staticfiles','rest_framework','rest_framework_simplejwt','drf_spectacular','corsheaders','monitoring']
MIDDLEWARE=['django.middleware.security.SecurityMiddleware','corsheaders.middleware.CorsMiddleware','django.contrib.sessions.middleware.SessionMiddleware','django.middleware.common.CommonMiddleware','django.middleware.csrf.CsrfViewMiddleware','django.contrib.auth.middleware.AuthenticationMiddleware','django.contrib.messages.middleware.MessageMiddleware','django.middleware.clickjacking.XFrameOptionsMiddleware']
ROOT_URLCONF='config.urls'
TEMPLATES=[{'BACKEND':'django.template.backends.django.DjangoTemplates','DIRS':[],'APP_DIRS':True,'OPTIONS':{'context_processors':['django.template.context_processors.debug','django.template.context_processors.request','django.contrib.auth.context_processors.auth','django.contrib.messages.context_processors.messages']}}]
WSGI_APPLICATION='config.wsgi.application'
DATABASES={'default':{'ENGINE':'django.db.backends.postgresql','NAME':os.getenv('POSTGRES_DB','smartcity'),'USER':os.getenv('POSTGRES_USER','smartcity_read'),'PASSWORD':os.getenv('POSTGRES_PASSWORD',''),'HOST':os.getenv('POSTGRES_HOST','host.docker.internal'),'PORT':os.getenv('POSTGRES_PORT','5432'),'OPTIONS':{'options':'-c search_path=public,smart_city_schema'}}}
AUTH_PASSWORD_VALIDATORS=[{'NAME':'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},{'NAME':'django.contrib.auth.password_validation.MinimumLengthValidator'},{'NAME':'django.contrib.auth.password_validation.CommonPasswordValidator'},{'NAME':'django.contrib.auth.password_validation.NumericPasswordValidator'}]
REST_FRAMEWORK={'DEFAULT_AUTHENTICATION_CLASSES':['rest_framework_simplejwt.authentication.JWTAuthentication'],'DEFAULT_PERMISSION_CLASSES':['rest_framework.permissions.IsAuthenticatedOrReadOnly'],'DEFAULT_SCHEMA_CLASS':'drf_spectacular.openapi.AutoSchema','DEFAULT_THROTTLE_CLASSES':['rest_framework.throttling.AnonRateThrottle','rest_framework.throttling.UserRateThrottle'],'DEFAULT_THROTTLE_RATES':{'anon':'120/min','user':'300/min'}}
SIMPLE_JWT={'ACCESS_TOKEN_LIFETIME':timedelta(minutes=30),'REFRESH_TOKEN_LIFETIME':timedelta(days=1)}
SPECTACULAR_SETTINGS={'TITLE':'SmartCity Environmental Dashboard API','DESCRIPTION':'Public measurements, map and trend data; authenticated ML forecasts','VERSION':'1.0.0'}
CORS_ALLOWED_ORIGINS=[s for s in os.getenv('CORS_ALLOWED_ORIGINS','http://localhost:8080,http://localhost:5173').split(',') if s]
CSRF_TRUSTED_ORIGINS=CORS_ALLOWED_ORIGINS
LANGUAGE_CODE='en-us'; TIME_ZONE='Europe/Tirane'; USE_I18N=True; USE_TZ=True
STATIC_URL='static/';STATIC_ROOT=BASE_DIR/'staticfiles'; DEFAULT_AUTO_FIELD='django.db.models.BigAutoField'
SECURE_CONTENT_TYPE_NOSNIFF=True; SESSION_COOKIE_HTTPONLY=True
SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO','https') if os.getenv('TRUST_PROXY','false')=='true' else None
REDIS_URL=os.getenv('REDIS_URL','redis://redis:6379/0')
CACHES={'default':{'BACKEND':'django.core.cache.backends.redis.RedisCache','LOCATION':REDIS_URL}}
MQTT_HOST=os.getenv('MQTT_HOST','mosquitto');MQTT_PORT=int(os.getenv('MQTT_PORT','1883'));MQTT_TOPIC=os.getenv('MQTT_TOPIC','smartcity/nodes/+/measurements')
MQTT_USERNAME=os.getenv('MQTT_USERNAME','');MQTT_PASSWORD=os.getenv('MQTT_PASSWORD','')
MODEL_ENABLED=os.getenv('MODEL_ENABLED','true').lower()=='true'
