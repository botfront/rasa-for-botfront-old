from fbmessenger import MessengerClient
from flask import Blueprint, request, jsonify
from rasa_core.channels import UserMessage
from rasa_core.channels.facebook import MessengerBot, Messenger, FacebookInput
from fbmessenger.elements import Text as FBText
from fbmessenger.quick_replies import QuickReply, QuickReplies
from typing import Text, List, Dict, Any, Union
import bot.facebook_handoff as fbho
import logging
logger = logging.getLogger(__name__)


class MultiMessenger(Messenger):

    def __init__(self, page_access_token, on_new_message, handoff_info, fields):
        self.handoff_info = handoff_info
        self.fields = fields
        super().__init__(page_access_token, on_new_message)

    def _handle_user_message(self, text, sender_id):
        # type: (Text, Text) -> None
        """Pass on the text to the dialogue engine for processing."""
        fields = ','.join(self.fields) if self.fields else None
        out_channel = MultiMessengerBot(
            self.client,
            self.get_user(fields=fields),
            self.handoff_info)
        user_msg = UserMessage(text, out_channel, sender_id,
                               input_channel=self.name())

        # noinspection PyBroadException
        try:
            self.on_new_message(user_msg)
        except Exception:
            logger.exception("Exception when trying to handle webhook "
                             "for facebook message.")
            pass

    def message(self, message):
        # type: (Dict[Text, Any]) -> None
        """Handle an incoming event from the fb webhook."""

        if self._is_user_message(message):
            if 'quick_reply' in message['message']:
                text = message['message']['quick_reply']['payload']
            else:
                text = message['message']['text']
        elif self._is_audio_message(message):
            attachment = message['message']['attachments'][0]
            text = attachment['payload']['url']
        else:
            logger.warning("Received a message from facebook that we can not "
                           "handle. Message: {}".format(message))
            return

        self._handle_user_message(text, self.get_user_id())


class MultiMessengerBot(MessengerBot):

    @staticmethod
    def get_language(user):
        if 'locale' in user:
            split = user['locale'].split('_')
            if len(split) > 0:
                return split[0]
        return None

    def __init__(self, messenger_client, user, handoff_info):
        # type: (MessengerClient, dict) -> None

        self.user = user
        self.handoff_info = handoff_info
        self.language = self.get_language(user)
        super().__init__(messenger_client)

    def send_text_with_buttons(self, recipient_id, text, buttons, **kwargs):
        # type: (Text, Text, List[Dict[Text, Any]], Any) -> None
        """Sends buttons to the output."""

        quick_replies = QuickReplies([QuickReply(b['title'],
                                                 b['payload'],
                                                 b['image_url'] if 'image_url' in b else None,
                                                 'text') for b in buttons])

        self.send(recipient_id, FBText(text, quick_replies=quick_replies))

    def send_custom_message(self, recipient_id, payload):
        # type: (Text,  Union[Dict, List[Dict[Text, Any]]]) -> None
        """Sends elements to the output."""

        if payload.get('template_type') == 'handoff':
            if self.handoff_info:
                self.handoff_info['user'] = self.user
            return fbho.pass_thread_control(recipient_id,
                                            self.messenger_client.page_access_token,
                                            payload.get('expire_after', 60),
                                            handoff_info=self.handoff_info)

        if isinstance(payload, list):
            payload = {"payload": {
                "template_type": "generic",
                "elements": payload
            }}

        elif 'elements' in payload:
            for element in payload['elements']:
                if 'button' in element:
                    self._add_postback_info(element['buttons'])

        payload = {
            "attachment": {
                "type": "template",
                "payload": payload,
            }
        }
        result = self.messenger_client.send(payload, self._recipient_json(recipient_id), 'RESPONSE')
        if 'error' in result and 'message' in result:
            logger.error(result['message'])


class MultiFacebookInput(FacebookInput):
    """Facebook input channel implementation. Based on the HTTPInputChannel."""

    @classmethod
    def from_credentials(cls, credentials):
        if not credentials:
            cls.raise_missing_credentials_exception()

        return cls(credentials.get("verify"),
                   credentials.get("secret"),
                   credentials.get("page-access-token"),
                   credentials.get("page-id"),
                   credentials.get("handoff"),
                   credentials.get("fields"),
                   )

    def __init__(self, fb_verify, fb_secret, fb_access_token, fb_page_id,
                 handoff, fields):
        # type: (Text, Text, Text) -> None
        """Create a facebook input channel.

        Needs a couple of settings to properly authenticate and validate
        messages. Details to setup:

        https://github.com/rehabstudio/fbmessenger#facebook-app-setup

        Args:
            fb_verify: FB Verification string
                (can be chosen by yourself on webhook creation)
            fb_secret: facebook application secret
            fb_access_token: access token to post in the name of the FB page
        """
        self.fb_page_id = fb_page_id
        self.handoff = handoff
        self.fields = fields
        super().__init__(fb_verify, fb_secret, fb_access_token)

    def blueprint(self, on_new_message):

        fb_webhook = Blueprint('fb_webhook', __name__)

        @fb_webhook.route("/", methods=['GET'])
        def health():
            return jsonify({"status": "ok"})

        @fb_webhook.route("/webhook", methods=['GET'])
        def token_verification():
            if request.args.get("hub.verify_token") == self.fb_verify:
                return request.args.get("hub.challenge")
            else:
                logger.warning(
                    "Invalid fb verify token! Make sure this matches "
                    "your webhook settings on the facebook app.")
                return "failure, invalid token"

        @fb_webhook.route("/webhook", methods=['POST'])
        def webhook():
            signature = request.headers.get("X-Hub-Signature") or ''
            if not self.validate_hub_signature(self.fb_secret, request.data,
                                               signature):
                logger.warning("Wrong fb secret! Make sure this matches the "
                               "secret in your facebook app settings")
                return "not validated"

            messenger = MultiMessenger(self.fb_access_token, on_new_message, self.handoff, self.fields)

            messenger.handle(fbho.apply_thread_control(
                request.get_json(force=True),
                self.handoff.get('expire-after', 60) if self.handoff else 0,
                self.fb_page_id,
                self.fb_access_token))

            return "success"

        return fb_webhook
