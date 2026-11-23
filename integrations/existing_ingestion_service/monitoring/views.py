import hashlib
import hmac
import json
import os
from pathlib import Path
from django.db import connection, DatabaseError
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from .services import ingest_payload, IngestError


def health(request):
    if request.method!='GET':return JsonResponse({'detail':'Method not allowed'},status=405)
    return JsonResponse({'status':'ok'})

@csrf_exempt
def ingest(request):
    if request.method!='POST':return JsonResponse({'detail':'POST required'},status=405)
    if os.getenv('API_REQUIRE_HTTPS','false').lower()=='true' and not request.is_secure():
        return JsonResponse({'detail':'HTTPS required'},status=403)
    token=request.headers.get('X-Api-Key','')
    if not token or len(token)>512:return JsonResponse({'detail':'Invalid API key'},status=401)
    hashed=hashlib.sha256(token.encode()).hexdigest()
    try:
        with connection.cursor() as cur:
            cur.execute('SELECT id, token_hash FROM smart_city_schema.api_users WHERE is_active=true')
            matched=next((id for id,stored in cur.fetchall() if hmac.compare_digest(stored,hashed)),None)
        if matched is None:return JsonResponse({'detail':'Invalid API key'},status=401)
        if len(request.body)>int(os.getenv('API_MAX_BODY_BYTES','262144')):
            return JsonResponse({'detail':'Body too large'},status=413)
        try: payload=json.loads(request.body)
        except (ValueError,UnicodeDecodeError):return JsonResponse({'detail':'Malformed JSON'},status=400)
        try: result=ingest_payload(payload,matched,request.path)
        except IngestError as exc:return JsonResponse({'detail':str(exc)},status=422)
        with connection.cursor() as cur:
            cur.execute('UPDATE smart_city_schema.api_users SET last_used_at=now() WHERE id=%s',[matched])
        # Always 200; original sensor send_to_api and offline replay use 200 as success.
        return JsonResponse(result,status=200)
    except DatabaseError:
        return JsonResponse({'detail':'Database unavailable'},status=503)


def openapi(request):
    doc=Path(__file__).resolve().parent.parent/'openapi.json'
    return HttpResponse(doc.read_text(),content_type='application/json')


def docs(request):
    return HttpResponse('''<!DOCTYPE html><html><head><title>SmartCity API</title>
<link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css"></head>
<body><div id="swagger-ui"></div>
<script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
<script>SwaggerUIBundle({url:'/api/openapi.json',dom_id:'#swagger-ui'});</script></body></html>''',content_type='text/html')
