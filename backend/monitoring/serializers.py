from rest_framework import serializers
class WindowSerializer(serializers.Serializer):
 window=serializers.ChoiceField(choices=['month','2weeks','week','3days','2days','day','3hours','now'],default='now')
 param=serializers.ChoiceField(choices=['pm25','pm10','temperature','humidity','pressure','uv','noise'],default='pm25')
 mode=serializers.ChoiceField(choices=['observed','forecast'],default='observed')
class ForecastRequestSerializer(serializers.Serializer):
 city=serializers.ChoiceField(choices=['Tirana','Elbasan','Korca'],required=False)
 horizon_hours=serializers.IntegerField(min_value=1,max_value=72,default=24)
