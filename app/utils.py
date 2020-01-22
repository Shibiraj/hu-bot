import json

import requests
from django.conf import settings
from django.db.models import Q
from twilio.rest import Client

from app.models import MyUser, Votes

FB_ENDPOINT = 'https://graph.facebook.com'
endpoint = f"{FB_ENDPOINT}/me/messages?access_token={settings.FB_PAGE_TOKEN}"


class TwillioManager():

    def __init__(self):
        account_sid = settings.TWILIO_ACCOUNT_SID
        auth_token = settings.TWILIO_API_KEY
        self.client = Client(account_sid, auth_token)

    def send_message(self, to, msg):
        to = 'whatsapp:{}'.format(to)
        message = self.client.messages.create(
            from_='whatsapp:+14155238886',
            body=msg,
            to=to)
        return message.sid


def get_message_details(data):
    mob = msg = None
    try:
        mob = data['From'][0].replace('whatsapp:', '')
        msg = data['Body'][0]
    except KeyError:
        pass
    return mob, msg


def check_user(fbid, name='user'):
    if not MyUser.objects.filter(username=fbid).first():
        password = 'Test@123'
        ob = MyUser.objects.create(username=fbid, first_name=name, address='chicago')
        ob.set_password(password)
        ob.save()


# {
#     "sender":{
#         "id":"<PSID>"
#     },
#     "recipient":{
#         "id":"<PAGE_ID>"
#     },
#     "timestamp":1458692752478,
#     "message":{
#         "mid":"mid.1457764197618:41d102a3e1ae206a38",
#         "text":"hello, world!",
#         "quick_reply": {
#             "payload": "<DEVELOPER_DEFINED_PAYLOAD>"
#         }
#     }
# }

def fb_msg_details(message):
    recipient = msg = None
    try:
        recipient = message['recipient']
        msg = message['message']['text']
    except:
        pass
    return recipient, msg


def same_old(l1, l2):
    lower = lambda x: [i.lower() for i in x]
    return bool(set(lower(l1)) & set(lower(l2)))


def same(l1, l2):
    lower = lambda x: [i.lower() for i in x]
    return l2.lower() in lower(l1) or any([1 for i in l1 if i.lower() in l2.lower()])


def from_json(entities):
    result = []
    with open('lx-all.json', 'r') as f:
        json_data = json.load(f)

    for activity in json_data['activities']:
        if same(entities, activity['categories']):
            activity.update({'vote_count': get_upvote_count(activity['id'])})
            result.append(activity)
    result = sorted(result, key=lambda x: x['vote_count'])
    return result


def get_full_activity(entities):
    return from_json(entities)[:5]


def get_the_coumminty_fbid(fbid, address='chicago'):
    return list(
        MyUser.objects.filter(~Q(username=fbid) & Q(address=address) & Q(is_superuser=False)).values_list('username'))


def get_upvote_count(lx_id):
    vote = Votes.objects.filter(lx_id=lx_id).first()
    return vote.voted_by.count() if vote else 0


def get_entities(message):
    try:
        entities = [entity['value'] for entity in message['message']['nlp']['entities']['wit_tag'] if
                    entity['confidence'] > 0.7]
    except KeyError:
        entities = []
    return entities


def parser_incoming_message(incoming_message):
    result = {'fb_user_id': None, 'fb_user_txt': None, 'entities': []}
    for entry in incoming_message['entry']:
        for message in entry['messaging']:
            if 'message' in message:
                fb_user_id = message['sender']['id']  # sweet!
                check_user(fb_user_id)
                fb_user_txt = message['message'].get('text')
                result.update({'fb_user_id': fb_user_id, 'fb_user_txt': fb_user_txt, 'entities': get_entities(message)})
                break
    return result


def get_all_id():
    with open('lx-all.json', 'r') as f:
        json_data = json.load(f)
    return [activity['id'] for activity in json_data['activities']]


def get_template(activity, fbid):
    data = {
        "recipient": {
            "id": fbid
        },
        "message": {
            "attachment": {
                "type": "template",
                "payload": {
                    "template_type": "generic",
                    "elements": [
                        {
                            "title": activity['title'],
                            "image_url": activity['imageUrl'],
                            "subtitle": activity['shortDescription'],
                            "default_action": {
                                "type": "web_url",
                                "url": "https://petersfancybrownhats.com/view?item=103",
                                "webview_height_ratio": "tall",
                            },
                            "buttons": [
                                {
                                    "type": "web_url",
                                    "url": "https://wwwexpediacom.integration.sb.karmalab.net/things-to-do/{}".format(
                                        activity['formattedTitle']),
                                    "title": "View Website"
                                }, {
                                    "type": "web_url",
                                    "title": "Upvote",
                                    # "url": "https://b3025a6a.ngrok.io/upvote?lid=311106&fbid=2628411033946229",
                                    "url": "{}/upvote?lid={}&fbid={}".format(settings.URL, activity['id'], fbid),
                                    # "payload": "DEVELOPER_DEFINED_PAYLOAD"
                                }
                            ]
                        }
                    ]
                }
            }
        }
    }
    return data


def send_text_reply(fbid, msg):
    data = {"recipient": {"id": fbid}, "message": {"text": msg}}
    response_msg = json.dumps(data)
    status = requests.post(
        endpoint,
        headers={"Content-Type": "application/json"},
        data=response_msg)
    return status.json()


def send_to_others(entities, fbid):
    for recipient in get_the_coumminty_fbid(fbid):
        # print(recipient)
        pass
    recipient = fbid
    print('len is ', len(get_full_activity(entities)))
    for activity in get_full_activity(entities):
        data = get_template(activity, recipient)
        response_msg = json.dumps(data)
        status = requests.post(
            endpoint,
            headers={"Content-Type": "application/json"},
            data=response_msg)
        print(status.json())
    # return status.json()


def test(fbid):
    data = {
        "recipient": {
            "id": fbid
        },
        "message": {
            "attachment": {
                "type": "template",
                "payload": {
                    "template_type": "list",
                    "top_element_style": "compact",
                    "elements": [
                        {
                            "title": "Classic T-Shirt Collection",
                            "subtitle": "See all our colors",
                            "image_url": "https://media.int.expedia.com/int/localexpert/190061/52edad66-8804-4cd9-934f-87fb29cc7229.jpg?impolicy=resizecrop&rw=350&rh=197",
                            "buttons": [
                                {
                                    "title": "View",
                                    "type": "web_url",
                                    "url": "https://www.expedia.com/",
                                    "messenger_extensions": True,
                                    "webview_height_ratio": "tall",
                                    "fallback_url": "https://www.expedia.com/"
                                }
                            ]
                        },
                        {
                            "title": "Classic White T-Shirt",
                            "subtitle": "See all our colors",
                            "default_action": {
                                "type": "web_url",
                                "url": "https://www.expedia.com/",
                                "messenger_extensions": False,
                                "webview_height_ratio": "tall"
                            }
                        },
                        {
                            "title": "Classic Blue T-Shirt",
                            "image_url": "https://media.int.expedia.com/int/localexpert/190061/52edad66-8804-4cd9-934f-87fb29cc7229.jpg?impolicy=resizecrop&rw=350&rh=197",
                            "subtitle": "100% Cotton, 200% Comfortable",
                            "default_action": {
                                "type": "web_url",
                                "url": "https://www.expedia.com/",
                                "messenger_extensions": True,
                                "webview_height_ratio": "tall",
                                "fallback_url": "https://www.expedia.com/"
                            },
                            "buttons": [
                                {
                                    "title": "Shop Now",
                                    "type": "web_url",
                                    "url": "https://www.expedia.com/",
                                    "messenger_extensions": True,
                                    "webview_height_ratio": "tall",
                                    "fallback_url": "https://www.expedia.com/"
                                }
                            ]
                        }
                    ],
                    "buttons": [
                        {
                            "title": "View More",
                            "type": "postback",
                            "payload": "payload"
                        }
                    ]
                }
            }
        }
    }
    response_msg = json.dumps(data)
    status = requests.post(
        endpoint,
        headers={"Content-Type": "application/json"},
        data=response_msg)
    print(status.json())
