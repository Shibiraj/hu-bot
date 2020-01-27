import json

import requests
from django.conf import settings
from django.db.models import Q
from twilio.rest import Client

from app.models import MyUser, Votes, History

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


def check_user_name(fbid):
    user = MyUser.objects.filter(username=fbid).first()
    return user.first_name if user and user.first_name else ''


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
    result = sorted(result, key=lambda x: x['vote_count'], reverse=True)
    return result


def get_full_activity(entities):
    return from_json(entities)[:5]


def get_the_coumminty_fbid(fbid, address='chicago'):
    return [i[0] for i in
            MyUser.objects.filter(~Q(username=fbid) & Q(address=address) & Q(is_superuser=False)).values_list(
                'username')]


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


def get_intents(message):
    try:
        intents = [intent['value'] for intent in message['message']['nlp']['entities']['intent']]
    except KeyError:
        intents = []
    return intents


def parser_incoming_message(incoming_message):
    result = {'fb_user_id': None, 'fb_user_txt': None, 'entities': [], 'intents': [], 'payload': None}
    for entry in incoming_message['entry']:
        for message in entry['messaging']:
            fb_user_id = message['sender']['id']  # sweet!
            result.update({'fb_user_id': fb_user_id})
            if 'message' in message:
                entities = get_entities(message)
                intents = get_intents(message)
                fb_user_txt = message['message'].get('text')
                result.update({'fb_user_txt': fb_user_txt, 'entities': entities,
                               'intents': intents})
            if 'postback' in message:
                result.update({'payload': message['postback']['payload']})
            break
    return result


def get_all_id():
    with open('lx-all.json', 'r') as f:
        json_data = json.load(f)
    return [activity['id'] for activity in json_data['activities']]


def get_template(activities, fbid, others):
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
                    ]
                }
            }
        }
    }
    elements = []
    for activity in activities:
        element = {
            "title": activity['title'],
            "image_url": activity['imageUrl'],
            "subtitle": activity['shortDescription'],
            "default_action": {
                "type": "web_url",
                "url": "https://wwwexpediacom.integration.sb.karmalab.net/things-to-do/{}".format(
                    activity['formattedTitle']),
                "webview_height_ratio": "tall",
            },
            "buttons": [
                {
                    "type": "web_url",
                    "url": "https://wwwexpediacom.integration.sb.karmalab.net/things-to-do/{}".format(
                        activity['formattedTitle']),
                    "title": "View Website"
                }
            ]
        }
        if others:
            upvote_dict = {
                "type": "postback",
                "title": "Upvote",
                "payload": activity['id']
            }
            element['buttons'].append(upvote_dict)
        elements.append(element)

    data['message']['attachment']['payload']['elements'] = elements
    return data


def send_text_reply(fbid, msg):
    data = {"recipient": {"id": fbid}, "message": {"text": msg}}
    response_msg = json.dumps(data)
    status = requests.post(
        endpoint,
        headers={"Content-Type": "application/json"},
        data=response_msg)
    return status.json()


def is_already_sent(sender, req_user):
    return History.objects.filter(user__username=sender, is_active=True, req_user=req_user).first() is not None


def send_lx(entities, fbid, others=True):
    already_sent = False
    if others:
        for recipient in get_the_coumminty_fbid(fbid):
            if not is_already_sent(recipient, fbid):
                if not already_sent:
                    reply = 'Your question has been forwarded to the community, Please wait..'
                    send_text_reply(fbid, reply)
                already_sent = True
                user = MyUser.objects.filter(username=recipient).first()
                History.objects.create(user=user, req_user=fbid)
                activities = get_full_activity(entities)
                data = get_template(activities, recipient, others)
                response_msg = json.dumps(data)
                status = requests.post(
                    endpoint,
                    headers={"Content-Type": "application/json"},
                    data=response_msg)
                print(status.json())

    else:
        activities = get_full_activity(entities)
        data = get_template(activities, fbid, others)
        response_msg = json.dumps(data)
        status = requests.post(
            endpoint,
            headers={"Content-Type": "application/json"},
            data=response_msg)
        History.objects.filter(req_user=fbid).all().delete()
        print(status.json())


def show_all_categories(fbid):
    data = {
        "recipient": {
            "id": fbid
        },
        "messaging_type": "RESPONSE",
        "message": {
            "text": "Please choose a category:",
            "quick_replies": [
                {
                    "content_type": "text",
                    "title": "Adventure",
                    "payload": "",
                    # "image_url":"https://i.ibb.co/bNrfXJZ/blue-circle-png-1.png"
                }, {
                    "content_type": "text",
                    "title": "Romantic",
                    "payload": "<POSTBACK_PAYLOAD>",
                    # "image_url":"https://i.ibb.co/bNrfXJZ/blue-circle-png-1.png"
                }, {
                    "content_type": "text",
                    "title": "Historic",
                    "payload": "<POSTBACK_PAYLOAD>",
                    # "image_url":"https://i.ibb.co/bNrfXJZ/blue-circle-png-1.png"
                }
            ]
        }
    }
    response_msg = json.dumps(data)
    status = requests.post(
        endpoint,
        headers={"Content-Type": "application/json"},
        data=response_msg)
    print(status.json())


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
                            "image_url": "https://media.int.expedia.com/int/localexpert/170364/9d32855e-6daf-4965-b333-b690b4595887.jpg?impolicy=resizecrop&rw=350&rh=197",
                            "buttons": [
                                {
                                    "title": "View",
                                    "type": "web_url",
                                    "url": "https://peterssendreceiveapp.ngrok.io/collection",
                                    "messenger_extensions": True,
                                    "webview_height_ratio": "tall",
                                    "fallback_url": "https://peterssendreceiveapp.ngrok.io/"
                                }
                            ]
                        },
                        {
                            "title": "Classic White T-Shirt",
                            "subtitle": "See all our colors",
                            "default_action": {
                                "type": "web_url",
                                "url": "https://media.int.expedia.com/int/localexpert/170364/9d32855e-6daf-4965-b333-b690b4595887.jpg?impolicy=resizecrop&rw=350&rh=197",
                                "messenger_extensions": False,
                                "webview_height_ratio": "tall"
                            }
                        },
                        {
                            "title": "Classic Blue T-Shirt",
                            "image_url": "https://media.int.expedia.com/int/localexpert/170364/9d32855e-6daf-4965-b333-b690b4595887.jpg?impolicy=resizecrop&rw=350&rh=197",
                            "subtitle": "100% Cotton, 200% Comfortable",
                            "default_action": {
                                "type": "web_url",
                                "url": "https://media.int.expedia.com/int/localexpert/170364/9d32855e-6daf-4965-b333-b690b4595887.jpg?impolicy=resizecrop&rw=350&rh=197",
                                "messenger_extensions": True,
                                "webview_height_ratio": "tall",
                                "fallback_url": "https://media.int.expedia.com/int/localexpert/170364/9d32855e-6daf-4965-b333-b690b4595887.jpg?impolicy=resizecrop&rw=350&rh=197"
                            },
                            "buttons": [
                                {
                                    "title": "Shop Now",
                                    "type": "web_url",
                                    "url": "https://media.int.expedia.com/int/localexpert/170364/9d32855e-6daf-4965-b333-b690b4595887.jpg?impolicy=resizecrop&rw=350&rh=197",
                                    "messenger_extensions": True,
                                    "webview_height_ratio": "tall",
                                    "fallback_url": "https://media.int.expedia.com/int/localexpert/170364/9d32855e-6daf-4965-b333-b690b4595887.jpg?impolicy=resizecrop&rw=350&rh=197"
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
                            "image_url": "https://peterssendreceiveapp.ngrok.io/img/collection.png",
                            "buttons": [
                                {
                                    "title": "View",
                                    "type": "web_url",
                                    "url": "https://peterssendreceiveapp.ngrok.io/collection",
                                    "messenger_extensions": True,
                                    "webview_height_ratio": "tall",
                                    "fallback_url": "https://peterssendreceiveapp.ngrok.io/"
                                }
                            ]
                        },
                        {
                            "title": "Classic White T-Shirt",
                            "subtitle": "See all our colors",
                            "default_action": {
                                "type": "web_url",
                                "url": "https://peterssendreceiveapp.ngrok.io/view?item=100",
                                "messenger_extensions": False,
                                "webview_height_ratio": "tall"
                            }
                        },
                        {
                            "title": "Classic Blue T-Shirt",
                            "image_url": "https://peterssendreceiveapp.ngrok.io/img/blue-t-shirt.png",
                            "subtitle": "100% Cotton, 200% Comfortable",
                            "default_action": {
                                "type": "web_url",
                                "url": "https://peterssendreceiveapp.ngrok.io/view?item=101",
                                "messenger_extensions": True,
                                "webview_height_ratio": "tall",
                                "fallback_url": "https://peterssendreceiveapp.ngrok.io/"
                            },
                            "buttons": [
                                {
                                    "title": "Shop Now",
                                    "type": "web_url",
                                    "url": "https://peterssendreceiveapp.ngrok.io/shop?item=101",
                                    "messenger_extensions": True,
                                    "webview_height_ratio": "tall",
                                    "fallback_url": "https://peterssendreceiveapp.ngrok.io/"
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
