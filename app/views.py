from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View

from app.utils import *

FB_ENDPOINT = 'https://graph.facebook.com/v2.12/'


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
            msg_details = parser_incoming_message(incoming_message)
            print('msg_details', len(msg_details['entities']), msg_details)
            with open('mess_in.txt', 'a+') as w:
                w.write('\n{}\n{}'.format(incoming_message, msg_details))

            if msg_details['fb_user_txt'] == 'test':
                test(msg_details['fb_user_id'])
            elif msg_details['entities']:
                send_to_others(msg_details['entities'], msg_details['fb_user_id'])
            else:
                send_text_reply(msg_details['fb_user_id'], 'Entities not found')
        except Exception as e:
            print(e)
            with open('error_fb.txt', 'a+') as w:
                w.write('\n{}\n'.format(e))
        finally:
            return HttpResponse("Success", status=200)


@csrf_exempt
def upvote(request):
    if request.method == 'GET':
        lx_id = request.GET.get('lid', None)
        fbid = request.GET.get('fbid', None)
        user = MyUser.objects.filter(username=fbid).first()
        vote = Votes.objects.filter(lx_id=lx_id).first()
        if user is not None and vote is not None and user not in vote.voted_by.all():
            vote.voted_by.add(user)
            return HttpResponse("<h1>Successfully up-voted.</h1>")
        else:
            return HttpResponse("<h1>You have already up-voted.</h1>")


@csrf_exempt
def msg_in(request):
    if request.method == 'POST':
        with open('indata.txt', 'a+') as w:
            w.write('\n{}\n{}'.format(request.POST, request.body))
        data = dict(request.POST)
        mob, msg = get_message_details(data)
        obj = TwillioManager()
        if 'add-user' in msg.lower():
            add_user(msg)
            msg = 'User details successfully saved ..!'
        else:
            user = MyUser.objects.filter(username=mob.replace('+91', '')).first()
            name = user.first_name if user is not None else ''
            msg = 'Hi {},\nHow can I help you ?'.format(name)
        obj.send_message(mob, msg)
        return JsonResponse({'status': 'success'})


@csrf_exempt
def call_back(request):
    if request.method == 'GET':
        import pickle
        pickle.dump(request, 'request.pickle')
        return JsonResponse({'foo': 'bar'})

    if request.method == 'POST':
        with open('ourdata.txt', 'a+') as w:
            w.write('\n{}\n{}'.format(request.POST, request.body))
        print(request.POST)

        return JsonResponse({'foo': 'bar'})


class TestView(View):

    def get(self, request):
        return render(request, 'test.html')

    def post(self, request):
        with open('ourdata.txt', 'w') as w:
            w.write(request.POST)

        print(request.POST)
        return JsonResponse({'foo': 'bar'})
