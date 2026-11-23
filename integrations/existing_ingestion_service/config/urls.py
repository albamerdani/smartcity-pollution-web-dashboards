from django.urls import path
from monitoring.views import ingest,health,openapi,docs
urlpatterns=[path('health/',health),path('api/v1/ingest/',ingest),path('api/openapi.json',openapi),path('api/docs/',docs)]
