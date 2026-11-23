from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse
from rest_framework.decorators import api_view,permission_classes,throttle_classes
from rest_framework.permissions import AllowAny,IsAdminUser
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import WindowSerializer,ForecastRequestSerializer
from .services.measurements import query_latest,timeseries,CITIES,CITY_CENTERS
from .services.forecast import run_cached
from .services.mqtt import store_live
from django.conf import settings
from django.utils import timezone
class StaffLoginView(TokenObtainPairView):
 permission_classes=[AllowAny]
 def post(self,request,*args,**kwargs):
  from django.contrib.auth import authenticate
  user=authenticate(username=request.data.get('username'),password=request.data.get('password'))
  if not user or not user.is_staff:return Response({'detail':'Staff account required'},status=401)
  return super().post(request,*args,**kwargs)
@api_view(['GET'])
@permission_classes([AllowAny])
def health(request):
 try:
  with connection.cursor() as c:c.execute('SELECT 1');c.fetchone()
  return Response({'status':'ok','database':'connected'})
 except Exception:return Response({'status':'degraded','database':'unavailable'},status=503)
@api_view(['GET'])
@permission_classes([AllowAny])
def map_points(request):
 s=WindowSerializer(data=request.query_params);s.is_valid(raise_exception=True)
 data=s.validated_data
 points=query_latest(data['window'],data['param'])
 if data['mode']=='forecast':
  forecast=cache.get('smartcity:latest_forecast') or {}
  # select prediction per node and field, default +1 h; must be explicitly requested
  by_node={}
  for f in forecast.get('forecasts',[]):
   if f.get('param')==data['param'] and f.get('node') not in by_node:by_node[f['node']]=f
  for item in points:
   match=by_node.get(item['node'])
   if match:item.update(value=match['value'],timestamp=match['timestamp'],source='forecast',forecast_method=match['method'])
 return Response({'window':data['window'],'param':data['param'],'mode':data['mode'],'cities':CITY_CENTERS,'points':points,'count':len(points),'generated_at':timezone.now().isoformat()})
@api_view(['GET'])
@permission_classes([AllowAny])
def trends(request):
 s=WindowSerializer(data=request.query_params);s.is_valid(raise_exception=True)
 city=request.query_params.get('city')
 if city and city not in CITIES:return Response({'detail':'Invalid city'},status=400)
 d=s.validated_data
 return Response({'window':d['window'],'param':d['param'],'series':timeseries(d['window'],d['param'],city)})
@api_view(['GET'])
@permission_classes([AllowAny])
def overview(request):
 points=query_latest('now','pm25')
 return Response({'cities':CITIES,'nodes_online':sum(not x['stale'] for x in points),'nodes_with_pm25':len(points),'points':points})
@api_view(['GET','POST'])
@permission_classes([IsAdminUser])
def forecasts(request):
 s=ForecastRequestSerializer(data=request.data if request.method=='POST' else request.query_params);s.is_valid(raise_exception=True)
 result=run_cached(s.validated_data.get('city'),s.validated_data['horizon_hours'])
 cache.set('smartcity:latest_forecast',result,600)
 return Response(result)
