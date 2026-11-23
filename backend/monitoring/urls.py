from django.urls import path
from . import views
urlpatterns=[path('health/',views.health),path('login/',views.StaffLoginView.as_view()),path('map/',views.map_points),path('trends/',views.trends),path('overview/',views.overview),path('forecasts/',views.forecasts)]
