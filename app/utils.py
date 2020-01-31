import json

import requests
from django.conf import settings
from django.db.models import Q
from twilio.rest import Client

from app.models import MyUser, Votes, History, RestaurantVote

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


def get_full_data(entities, type='visit'):
    if type == 'visit':
        result = []
        with open('lx-all.json', 'r') as f:
            json_data = json.load(f)

        for activity in json_data['activities']:
            if same(entities, activity['categories']):
                activity.update({'vote_count': get_upvote_count(activity['id'])})
                result.append(activity)
        result = sorted(result, key=lambda x: x['vote_count'], reverse=True)

        return result[:5]
    else:
        result = []
        with open('hotels.json', 'r') as f:
            json_data = json.load(f)

        for activity in json_data['restaurants']:
            if same(entities, activity['categories']):
                activity.update({'vote_count': get_upvote_count(activity['id'], 'hotels')})
                result.append(activity)
        result = sorted(result, key=lambda x: x['vote_count'], reverse=True)
        return result


def get_the_coumminty_fbid(fbid, address='chicago'):
    return [i[0] for i in
            MyUser.objects.filter(~Q(username=fbid) & Q(address=address) & Q(is_superuser=False)).values_list(
                'username')]


def get_upvote_count(lx_id, type='activity'):
    if type == 'activity':
        vote = Votes.objects.filter(lx_id=lx_id).first()
        return vote.voted_by.count() if vote else 0
    else:
        vote = RestaurantVote.objects.filter(rest_id=lx_id).first()
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
    result = {'fb_user_id': None, 'fb_user_txt': None, 'entities': [], 'intents': [], 'payload': None,
              'attachment': None, 'quick_reply': None}
    for entry in incoming_message['entry']:
        for message in entry['messaging']:
            fb_user_id = message['sender']['id']  # sweet!
            result.update({'fb_user_id': fb_user_id})
            if 'message' in message:
                entities = get_entities(message)
                intents = get_intents(message)
                fb_user_txt = message['message'].get('text')
                attachment = message['message'].get('attachments')
                quick_reply = message['message'].get('quick_reply').get('payload') if message['message'].get(
                    'quick_reply') else None
                attachment = attachment[0] if attachment and len(attachment) > 0 else None
                result.update({'fb_user_txt': fb_user_txt, 'entities': entities,
                               'intents': intents, 'attachments': attachment, 'quick_reply': quick_reply})
            if 'postback' in message:
                result.update({'payload': message['postback']['payload']})
            break
    return result


def get_all_id():
    with open('lx-all.json', 'r') as f:
        json_data = json.load(f)
    return [activity['id'] for activity in json_data['activities']]


def get_template(activities, fbid, upvote_option, type):
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
                    activity['formattedTitle']) if not activity.get('website') else activity.get('website'),
                "webview_height_ratio": "tall",
            },
            "buttons": [
                {
                    "type": "web_url",
                    "url": "https://wwwexpediacom.integration.sb.karmalab.net/things-to-do/{}".format(
                        activity['formattedTitle']) if not activity.get('website') else activity.get('website'),
                    "title": "View Website"
                }
            ]
        }
        if upvote_option:
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


def send_result(entities, fbid, upvote_option=True, type='visit'):
    if upvote_option:
        reply = 'Your question has been forwarded to the community, Please wait..'
        send_text_reply(fbid, reply)
        for recipient in get_the_coumminty_fbid(fbid):
            if recipient.lower() == '2769736776454856':
                continue
            _type = 'adventurous activities' if type == 'visit' else 'Italian restaurants'
            msg = 'A fellow traveler has asked your suggestion about best {} near Chicago'.format(_type)
            send_text_reply(recipient, msg)
            activities = get_full_data(entities, type)
            data = get_template(activities, recipient, upvote_option, type)
            response_msg = json.dumps(data)
            status = requests.post(
                endpoint,
                headers={"Content-Type": "application/json"},
                data=response_msg)
            print(status.json())

    else:
        activities = get_full_data(entities, type)
        data = get_template(activities, fbid, upvote_option, type)
        response_msg = json.dumps(data)
        status = requests.post(
            endpoint,
            headers={"Content-Type": "application/json"},
            data=response_msg)
        if type != 'visit':
            reply = "Here are the local expert suggestions."
            send_text_reply(fbid, reply)
            image = 'https://i.ibb.co/RvVSXJV/Webp-net-compress-image.jpg'

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
                                    "title": "Found Hotel Chicago",
                                    "image_url": image,
                                    "subtitle": '613 N Wells St, Chicago, Illinois 60654',
                                    "buttons": [
                                        {
                                            "type": "web_url",
                                            "url": "https://wego.here.com/directions/mix//:e-eyJuYW1lIjoiIiwiYWRkcmVzcyI6IiIsImxhdGl0dWRlIjowLCJsb25naXR1ZGUiOjB9?map=52.50795,13.67088,15,normal&fb_locale=en_US",
                                            "title": "View suggestion"
                                        }
                                    ]
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


def show_all_categories(fbid, type):
    if type == 'visit':
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
                        "payload": "Adventure",
                    }, {
                        "content_type": "text",
                        "title": "Romantic",
                        "payload": "Romantic",
                    }, {
                        "content_type": "text",
                        "title": "Historic",
                        "payload": "Historic",
                    }
                ]
            }
        }
    else:
        data = {
            "recipient": {
                "id": fbid
            },
            "messaging_type": "RESPONSE",
            "message": {
                "text": "Please choose a cuisine type:",
                "quick_replies": [
                    {
                        "content_type": "text",
                        "title": "Italian",
                        "payload": "Italian",
                    },
                    {
                        "content_type": "text",
                        "title": "Japanese",
                        "payload": "Japanese",
                    }, {
                        "content_type": "text",
                        "title": "Asian",
                        "payload": "Asian",
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
    fbid = '3380788151996251'
    data = {
        "recipient": {
            "id": fbid
        },
        "messaging_type": "RESPONSE",
        "message": {
            "text": "Pick a color:",
            "quick_replies": [
                {
                    "content_type": "location"
                }
            ]
        }
    }
    data = {
        "recipient": {
            "id": fbid
        },
        "messaging_type": "RESPONSE",
        "message": {
            "text": "Please choose a category:",
            "quick_replies": [
                {
                    "content_type": "user_phone_number",
                    "title": "+98876767967676",
                }
            ]
        }
    }
    lat, long = '55', '37'
    data = {
        "recipient": {"id": fbid},
        "message": {
            "attachment": {
                "type": "template",
                "payload": {
                    "template_type": "generic",
                    "elements": {
                        "element": {
                            "title": "Your current location",
                            "image_url": "https:\/\/maps.googleapis.com\/maps\/api\/staticmap?size=764x400&center=" + lat + "," + long + "&zoom=25&markers=" + lat + "," + long,
                            "item_url": "http:\/\/maps.apple.com\/maps?q=" + lat + "," + long + "&z=16"
                        }
                    }
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
    return
