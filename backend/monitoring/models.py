"""Read-only representations of the existing PostgreSQL 16/TimescaleDB tables.
Django does not create or migrate the legacy smart_city_schema tables.
"""
from django.db import models
class City(models.Model):
 city_name=models.TextField(unique=True)
 country_name=models.TextField()
 notes=models.TextField(null=True)
 class Meta: managed=False;db_table='smart_city_schema"."cities'
class Location(models.Model):
 city=models.ForeignKey(City,db_column='city_id',on_delete=models.DO_NOTHING,null=True)
 location_name=models.TextField()
 latitude=models.FloatField(null=True);longitude=models.FloatField(null=True);elevation_m=models.FloatField(null=True);description=models.TextField(null=True)
 class Meta:managed=False;db_table='smart_city_schema"."locations'
class Node(models.Model):
 node_name=models.TextField(unique=True)
 node_external_id=models.TextField(null=True);node_type=models.TextField();communication_type=models.TextField()
 location=models.ForeignKey(Location,db_column='location_id',on_delete=models.DO_NOTHING,null=True)
 active=models.BooleanField(default=True)
 class Meta:managed=False;db_table='smart_city_schema"."nodes'
class EnvironmentalMeasurement(models.Model):
 id=models.BigIntegerField(primary_key=True)
 measured_at=models.DateTimeField()
 node=models.ForeignKey(Node,db_column='node_id',on_delete=models.DO_NOTHING)
 temperature_c=models.FloatField(null=True);humidity_pct=models.FloatField(null=True)
 pm25_ug_m3=models.FloatField(null=True);pm10_ug_m3=models.FloatField(null=True)
 class Meta: managed=False;db_table='smart_city_schema"."environmental_measurements'
