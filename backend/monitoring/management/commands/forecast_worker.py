import logging,time
from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.cache import cache
from monitoring.services.forecast import generate
logger=logging.getLogger(__name__)
class Command(BaseCommand):
 help='Run rolling model forecasts using database history (every FORECAST_INTERVAL_SECONDS)'
 def handle(self,*args,**kwargs):
  import os
  seconds=max(60,int(os.getenv('FORECAST_INTERVAL_SECONDS','300')))
  while True:
   try:
    result=generate(horizon=24)
    cache.set('smartcity:latest_forecast',result,seconds*3)
    cache.set('smartcity:forecast:all:24',result,seconds*2)
    logger.info('Forecast %s, %d rows',result['status'],len(result.get('forecasts',[])))
   except Exception:logger.exception('Forecast refresh failed')
   time.sleep(seconds)
