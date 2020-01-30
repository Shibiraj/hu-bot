from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from app.tasks import handle_webhook_request
from app.utils import *


@csrf_exempt
def webhook(request):
    if request.method == 'GET':
        hub_mode = request.GET.get('hub.mode')
        hub_token = request.GET.get('hub.verify_token')
        hub_challenge = request.GET.get('hub.challenge')
        if hub_token != settings.FB_PAGE_TOKEN:
            return HttpResponse('Error, invalid token', status_code=403)
        return HttpResponse(hub_challenge)

    if request.method == 'POST':
        try:
            incoming_message = json.loads(request.body.decode('utf-8'))
            task = handle_webhook_request.delay(incoming_message)
        except Exception as e:
            pass
        finally:
            return HttpResponse("Success", status=200)
