import logging
import uuid
from typing import Optional, Text
from typing import Optional, Text, Any, List, Dict

import socketio
from flask import Blueprint, jsonify

from rasa_core.channels import InputChannel
from rasa_core.channels.channel import (
    UserMessage,
    OutputChannel)

logger = logging.getLogger(__name__)


class SocketBlueprint(Blueprint):
    def __init__(self, sio, socketio_path, *args, **kwargs):
        self.sio = sio
        self.socketio_path = socketio_path
        super(SocketBlueprint, self).__init__(*args, **kwargs)

    def register(self, app, options, first_registration=False):
        app.wsgi_app = socketio.Middleware(self.sio, app.wsgi_app, self.socketio_path)
        super(SocketBlueprint, self).register(app, options, first_registration)


class SocketIOOutput(OutputChannel):

    @classmethod
    def name(cls):
        return "socketio"

    def __init__(self, sio, sid, bot_message_evt):
        self.sio = sio
        self.sid = sid
        self.custom_data = None
        self.language = None
        self.bot_message_evt = bot_message_evt

    def set_custom_data(self, custom_data):
        self.custom_data = custom_data

    def set_language(self, language):
        self.language = language

    def _send_message(self, socket_id, response):
        # type: (Text, Any) -> None
        """Sends a message to the recipient using the bot event."""
        self.sio.emit(self.bot_message_evt, response, room=socket_id)

    def send_text_message(self, recipient_id: Text, message: Text) -> None:
        """Send a message through this channel."""

        self._send_message(self.sid, {"text": message})

    def send_image_url(self, recipient_id: Text, image_url: Text) -> None:
        """Sends an image. Default will just post the url as a string."""
        message = {
            "attachment": {
                "type": "image",
                "payload": {"src": image_url}
            }
        }
        self._send_message(self.sid, message)

    def send_text_with_buttons(self, recipient_id: Text, text: Text,
                               buttons: List[Dict[Text, Any]],
                               **kwargs: Any) -> None:
        """Sends buttons to the output."""

        message = {
            "text": text,
            "quick_replies": []
        }

        for button in buttons:
            message["quick_replies"].append({
                "content_type": "text",
                "title": button['title'],
                "payload": button['payload']
            })

        self._send_message(self.sid, message)

    def send_custom_message(self, recipient_id: Text,
                            elements: List[Dict[Text, Any]]) -> None:
        """Sends elements to the output."""

        message = {"attachment": {
            "type": "template",
            "payload": {
                "template_type": "generic",
                "elements": elements[0]
            }}}

        self._send_message(self.sid, message)


class SocketIOInput(InputChannel):
    """A socket.io input channel."""

    @classmethod
    def name(cls):
        return "socketio"

    @classmethod
    def from_credentials(cls, credentials):
        credentials = credentials or {}
        return cls(credentials.get("user_message_evt", "user_uttered"),
                   credentials.get("bot_message_evt", "bot_uttered"),
                   credentials.get("namespace"),
                   credentials.get("session_persistence", False),
                   credentials.get("socketio_path", "/socket.io"),
                   )

    def __init__(self,
                 user_message_evt="user_uttered",  # type: Text
                 bot_message_evt="bot_uttered",  # type: Text
                 namespace=None,  # type: Optional[Text]
                 session_persistence=False,
                 socketio_path='/socket.io'  # type: Optional[Text]
                 ):
        self.bot_message_evt = bot_message_evt
        self.session_persistence = session_persistence
        self.user_message_evt = user_message_evt
        self.namespace = namespace
        self.socketio_path = socketio_path

    def blueprint(self, on_new_message):
        sio = socketio.Server()
        socketio_webhook = SocketBlueprint(sio, self.socketio_path, 'socketio_webhook', __name__)

        @socketio_webhook.route("/", methods=['GET'])
        def health():
            return jsonify({"status": "ok"})

        @sio.on('connect', namespace=self.namespace)
        def connect(sid, environ):
            logger.debug("User {} connected to socketio endpoint.".format(sid))

        @sio.on('disconnect', namespace=self.namespace)
        def disconnect(sid):
            logger.debug("User {} disconnected from socketio endpoint."
                         "".format(sid))

        @sio.on('session_request', namespace=self.namespace)
        def session_request(sid, data):
            if data is None:
                data = {}
            if 'session_id' not in data or data['session_id'] is None:
                data['session_id'] = uuid.uuid4().hex
            sio.emit("session_confirm", data['session_id'], room=sid)
            logger.debug("User {} connected to socketio endpoint."
                         "".format(sid))

        @sio.on(self.user_message_evt, namespace=self.namespace)
        def handle_message(sid, data):
            output_channel = SocketIOOutput(sio, sid, self.bot_message_evt)

            if self.session_persistence and ("session_id" not in data or data["session_id"] is None):
                logger.debug("A message without a valid sender_id was received")
            else:
                if 'customData' in data:
                    output_channel.set_custom_data(data['customData'])
                    if 'language' in data['customData']:
                        output_channel.set_language(data['customData']['language'])
                sender_id = data['session_id'] if self.session_persistence else sid
                message = UserMessage(data['message'], output_channel, sender_id,
                                      input_channel=self.name())
                on_new_message(message)

        return socketio_webhook
