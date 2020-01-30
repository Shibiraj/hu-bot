from celery import shared_task

from app.utils import *

FB_ENDPOINT = 'https://graph.facebook.com/v2.12/'


# @shared_task
# def make_dir(limit):
#     import time, os
#     print('reached 1')
#     time.sleep(limit)
#     print('reached 2')
#     os.mkdir('/Users/a-8525/Documents/shibi/myworkshop/cdx hackathon/hu-bot/xyz {}'.format(limit))
#     return 9+1

@shared_task
def handle_webhook_request(incoming_message):
    msg_details = parser_incoming_message(incoming_message)
    with open('mess_in.txt', 'a+') as w:
        w.write('\n{}\n{}'.format(incoming_message, msg_details))
    if msg_details['fb_user_id']:
        check_user(msg_details['fb_user_id'])
    print(msg_details)

    if msg_details['fb_user_txt'] and 'push' in msg_details['fb_user_txt'].lower():
        user_dict = {
            'rt': '2769736776454856',
            'sh': '2685531254857798',
            'rh': '3488020257935762',
            'sa': '2646325785465682'

        }
        category_dict = {
            'a': 'adventure',
            'r': 'romantic',
            'h': 'historic'
        }
        user, cat = msg_details['fb_user_txt'].lower().strip().split(' ')[1:]

        send_lx([category_dict[cat]], user_dict[user], upvote_option=False)
        reply = 'pushed.'
        send_text_reply(msg_details['fb_user_id'], reply)

    elif msg_details['fb_user_txt'] and msg_details['fb_user_txt'].lower() == 'test':
        test(msg_details['fb_user_id'])

    elif msg_details['fb_user_txt'] and msg_details['fb_user_txt'].lower() == 'clear':
        for vote in Votes.objects.all():
            vote.voted_by.clear()
        History.objects.all().delete()
        reply = 'cleared.'
        send_text_reply(msg_details['fb_user_id'], reply)

    elif msg_details['payload']:
        lx_id = msg_details['payload']
        fbid = msg_details['fb_user_id']
        user = MyUser.objects.filter(username=fbid).first()
        vote = Votes.objects.filter(lx_id=lx_id).first()
        if user is not None and vote is not None and user not in vote.voted_by.all():
            vote.voted_by.add(user)
            reply = 'Thanks for your vote.'
        else:
            reply = 'You have already voted.'
        send_text_reply(msg_details['fb_user_id'], reply)

    elif msg_details['intents'] and 'Hello' in msg_details['intents']:
        reply = 'Hello {}, \nHow can I help you?'.format(check_user_name(msg_details['fb_user_id']))
        send_text_reply(msg_details['fb_user_id'], reply)

    elif msg_details['entities']:
        send_lx(msg_details['entities'], msg_details['fb_user_id'], upvote_option=True)

    else:
        show_all_categories(msg_details['fb_user_id'])
