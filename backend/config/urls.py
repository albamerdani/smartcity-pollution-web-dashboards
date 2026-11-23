from django.contrib import admin
from django.urls import path,include
from rest_framework_simplejwt.views import TokenRefreshView
from drf_spectacular.views import SpectacularAPIView,SpectacularSwaggerView
from monitoring import views
urlpatterns=[path('django-admin/',admin.site.urls),path('api/',include('monitoring.urls')),path('api/login/refresh/',TokenRefreshView.as_view()),path('api/schema/',SpectacularAPIView.as_view()),path('api/docs/',SpectacularSwaggerView.as_view(url_name='schema'))]
