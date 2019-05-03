from rasa_core_sdk import Action
from rasa_core_sdk.events import SlotSet, ConversationPaused, ConversationResumed, ReminderScheduled
import os
import requests
import logging
from datetime import datetime, timedelta

logging.basicConfig(level="WARN")
logger = logging.getLogger()


class ActionChitChat(Action):

    def name(self):
        return "action_chitchat"

    def run(self, dispatcher, tracker, domain):
        entities = tracker.latest_message["entities"]
        original_intent = list(filter(lambda e: e["entity"] == "intent", entities))[0]["value"]
        _, detail = original_intent.split(".")
        dispatcher.utter_template("utter_chitchat_{}".format(detail), tracker)
        return []


class ActionUtter(Action):

    def name(self):
        return 'action_utter'

    def run(self, dispatcher, tracker, domain):
        action = tracker.get_slot('followup_response_name')
        if action:
            dispatcher.utter_template(action, tracker)
        return [SlotSet('followup_response_name', None)]
    

class ActionFAQ(Action):

    def name(self):
        return 'action_faq'

    def run(self, dispatcher, tracker, domain):
        events = []
        entity_containing_intent = next((e for e in tracker.latest_message['entities'] if e['entity'] == 'intent'))

        payload = {"nlu": {
            "intent": entity_containing_intent["value"],
            "entities": list(
                map(lambda e: {"entity": e["entity"], "value": e["value"]},
                    filter(lambda e: e["entity"] != "intent", tracker.latest_message["entities"])))}}

        url = "{base_url}/project/{project_id}/response".format(
            base_url=os.environ.get('BF_URL'), project_id=os.environ.get("BF_PROJECT_ID"))
        try:
            response_sent = False
            result = requests.post(url, json=payload)

            if result.status_code == 200:
                response = result.json()
                response_name = response["key"]
                dispatcher.utter_template(response_name, tracker)
                response_sent = True
                events.append(SlotSet('latest_response_name', response_name))
                if 'follow_up' in response and response['follow_up'].get('action'):
                    if response['follow_up']['action'].startswith('utter'):
                        action = 'action_utter'
                        events.append(SlotSet('followup_response_name', response['follow_up']['action']))
                    # FollowUpAction produces random results, so we force a minimum delay for a reminder.
                    delay = max(2, int(response['follow_up']['delay']))
                    events.append(ReminderScheduled(
                        action,
                        datetime.now() + timedelta(seconds=delay),
                        kill_on_user_message=True))

            elif result.status_code == 404:
                logger.warning('Response not found for: {}'.format(str(payload)))
                events.append(SlotSet('latest_response_name', 'error_response_not_found'))
                if not response_sent:
                    dispatcher.utter_template("utter_fallback", tracker)
            else:
                logger.warning('Error {} with request: {}'.format(result.status_code, str(payload)))
                events.append(SlotSet('latest_response_name', 'error_unknown_error'))
                if not response_sent:
                    dispatcher.utter_template("utter_fallback", tracker)

        except StopIteration:
            logger.error('Error with request {}: {}'.format(str(payload), "No intent was passed as an entity"))
            events.append(SlotSet('latest_response_name', 'error_no_intent'))
            dispatcher.utter_template("utter_fallback", tracker)
        except Exception as e:
            logger.error('Error with request {}: {}'.format(str(payload), e))
            events.append(SlotSet('latest_response_name', 'error_unknown_error'))
            dispatcher.utter_template("utter_fallback", tracker)
        return events


class ActionPauseConversation(Action):

    def name(self):
        return 'action_pause_conversation'

    def run(self, dispatcher, tracker, domain):
        dispatcher.utter_template('utter_conversation_paused', tracker)
        return [ConversationPaused()]


class ActionResumeConversation(Action):

    def name(self):
        return 'action_conversation_resume'

    def run(self, dispatcher, tracker, domain):
        events = []
        print (tracker)
        if tracker.paused:
            events.append(ConversationResumed())

