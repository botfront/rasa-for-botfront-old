from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
import requests
import utils
from requests.auth import HTTPBasicAuth
import arrow
from pytz import UnknownTimeZoneError
import logging
logger = logging.getLogger(__name__)

try:
    handoff_scheduler = BackgroundScheduler()
    handoff_scheduler.start()
except UnknownTimeZoneError:
    logger.warning("apscheduler failed to start. "
                   "This is probably because your system timezone is not set"
                   "Set it with e.g. echo \"Europe/Berlin\" > /etc/timezone")


def pass_thread_control(recipient_id, page_token, expire_after=0, handoff_info=None):
    """ Initiates Facebook Handoff"""

    if handoff_info:
        send_handoff_email(recipient_id, handoff_info)

    # If we just want to trigger the notification but not pause the conversation until an agent is actually available
    if expire_after == 0:
        return

    url = "https://graph.facebook.com/v2.11/me/pass_thread_control?access_token={}".format(page_token)
    result = requests.post(url, json={
        "recipient": {"id": recipient_id},
        "target_app_id": 263902037430900,
        "metadata": ""
    })
    if result.status_code == 200:
        logger.debug("Handoff successfully activated for user {}".format(recipient_id))

        # We need to delay the action that pauses the conversation to make sure all events/actions
        # are append to the tracker first
        handoff_scheduler.add_job(execute_action,
                                  DateTrigger(run_date=arrow.utcnow().shift(seconds=2).datetime),
                                  args=['action_pause_conversation', recipient_id])

        # Schedule handoff cancellation
        schedule_or_reschedule_take_thread_control(recipient_id,
                                                   page_token,
                                                   expire_after)


def schedule_or_reschedule_take_thread_control(recipient_id, fb_acces_token, expire_after=0):
    """ Schedule a take thread control from the bot (handoff cancellation)"""

    def cancel_handoff(rid):
        url = "https://graph.facebook.com/v2.11/me/take_thread_control?access_token={}".format(
            fb_acces_token)
        result = requests.post(url, json={"recipient": {"id": rid}, "metadata": ""})
        if result.status_code != 200:
            import json
            logger.warning("Error when cancelling handoff for user {}: {}"
                           .format(recipient_id, json.dumps(result.json())))
        else:
            logger.debug("Handoff successfully cancelled for user {}".format(recipient_id))

    job = handoff_scheduler.get_job(recipient_id)
    if job:
        next_cancellation_datetime = arrow.utcnow().shift(seconds=int(job.name))
        job.reschedule(DateTrigger(run_date=next_cancellation_datetime.datetime))

        logger.debug("Handoff cancellation postponed to {} ({} secs later) for {}".format(
            next_cancellation_datetime,
            job.name,
            recipient_id))

    else:
        cancellation_datetime = arrow.utcnow().shift(seconds=expire_after)
        handoff_scheduler.add_job(cancel_handoff,
                                  DateTrigger(run_date=cancellation_datetime.datetime),
                                  args=[recipient_id],
                                  id=str(recipient_id),
                                  replace_existing=True,
                                  name=str(expire_after))  # storing the delay in the name to re-use when rescheduling

        logging.debug("Scheduling handoff cancellation for {} in {} secs at {})".format(
            recipient_id,
            expire_after,
            cancellation_datetime, ))


def cancel_take_thread_control(recipient_id):
    job = handoff_scheduler.get_job(recipient_id)
    if job:
        job.remove()


def execute_action(action, recipient_id):
    result = requests.post('http://localhost:5005/conversations/{}/execute'.format(recipient_id), json={'name': action})
    if result.status_code != 200:
        print(result.content)


def retrieve_tracker(recipient_id):
    result = requests.get('http://localhost:5005/conversations/{}/tracker'.format(recipient_id))
    if result.status_code == 200:
        return result.json()
    else:
        logging.error(result.content)


def apply_thread_control(payload, expire_after, page_id, page_token):
    if 'entry' in payload:
        # Resume bot
        for e in payload['entry']:
            if 'messaging' in e:
                for m in e['messaging']:
                    if 'pass_thread_control' in m:
                        cancel_take_thread_control(m['sender']['id'])
                        execute_action('action_resume_conversation', m['sender']['id'])
                        # execute_action('utter_conversation_resumed', m['sender']['id'])
                        m['message'] = {'text': '/system.resume_conversation'}
                        continue
                    elif 'message' in m and 'app_id' not in m['message'] and m['message'].get('is_echo', False):
                        pass_thread_control(m['recipient']['id'], page_token, expire_after)

            elif 'standby' in e:
                # Replace 'standby' with messaging so messages go to the tracker
                e['messaging'] = e.pop('standby')
                # schedule handoff cancellation
                if len(e['messaging']) and 'message' in e['messaging'][0]:
                    message = e['messaging'][0]
                    # The take thread control is related to the user id, we make sure to pick the right one
                    user_id = ({message['sender']['id'], message['recipient']['id']} - {str(page_id)})\
                        .pop()
                    schedule_or_reschedule_take_thread_control(user_id, page_token)

    return payload


def send_handoff_email(recipient_id, handoff_info):
    """Send email to hotel department when human intervention is required.
            Args:
                recipient_id (str): the fb page scoped ID
                handoff_info (dict): handoff info from credentials
            """

    events = retrieve_tracker(recipient_id)["events"]
    auth = HTTPBasicAuth(handoff_info['mailgun-user'], handoff_info['mailgun-password'])
    data = {
        'from': handoff_info['email-from'],
        'to': handoff_info['email-to'],
        'subject': handoff_info['email-subject'],
        'text': handoff_info['email-text'].format(
            user_info=get_user_info(handoff_info),
            conversation=utils.events_to_dialogue(events))
    }
    print(data)
    result = requests.post(handoff_info['mailgun-url'], data=data, auth=auth)
    print (result.json())


def get_user_info(handoff_info):
    return "\n".join(list(["{k}: {v}".format(k=k, v=v) for k, v in handoff_info["user"].items()]))