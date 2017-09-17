# Copyright (C) 2017 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Sample that implements gRPC client for Google Assistant API."""

import json
import logging
import os.path

import click

import grpc
import google.auth.transport.grpc
import google.auth.transport.requests
import google.oauth2.credentials

from google.assistant.embedded.v1alpha1 import embedded_assistant_pb2
from google.rpc import code_pb2
from tenacity import retry, stop_after_attempt, retry_if_exception

from breathing_led import BreathingLed
from push_button import PushButton
from push_button import PushButtonType
from boot_sound import BootSound

try:
    from . import (
        assistant_helpers,
        audio_helpers
    )
except SystemError:
    import assistant_helpers
    import audio_helpers

ASSISTANT_API_ENDPOINT = 'embeddedassistant.googleapis.com'
END_OF_UTTERANCE = embedded_assistant_pb2.ConverseResponse.END_OF_UTTERANCE
DIALOG_FOLLOW_ON = embedded_assistant_pb2.ConverseResult.DIALOG_FOLLOW_ON
CLOSE_MICROPHONE = embedded_assistant_pb2.ConverseResult.CLOSE_MICROPHONE
DEFAULT_GRPC_DEADLINE = 60 * 3 + 5

PUSH_TO_TALK_BUTTON_PIN = 14
PUSH_TO_TALK_BUTTON_SLEEP = 0.05

RED_BREATHING_LED_PIN = 18
red_breathing_led = BreathingLed(RED_BREATHING_LED_PIN)
gpio_setup_done = False


class SampleAssistant(object):
    """Sample Assistant that supports follow-on conversations.

    Args:
      conversation_stream(ConversationStream): audio stream
        for recording query and playing back assistant answer.
      channel: authorized gRPC channel for connection to the
        Google Assistant API.
      deadline_sec: gRPC deadline in seconds for Google Assistant API call.
    """

    def __init__(self, conversation_stream, channel, deadline_sec):
        self.conversation_stream = conversation_stream

        # Opaque blob provided in ConverseResponse that,
        # when provided in a follow-up ConverseRequest,
        # gives the Assistant a context marker within the current state
        # of the multi-Converse()-RPC "conversation".
        # This value, along with MicrophoneMode, supports a more natural
        # "conversation" with the Assistant.
        self.conversation_state = None

        # Create Google Assistant API gRPC client.
        self.assistant = embedded_assistant_pb2.EmbeddedAssistantStub(channel)
        self.deadline = deadline_sec

    def __enter__(self):
        return self

    def __exit__(self, etype, e, traceback):
        if e:
            return False
        self.conversation_stream.close()

    def is_grpc_error_unavailable(e):
        is_grpc_error = isinstance(e, grpc.RpcError)
        if is_grpc_error and (e.code() == grpc.StatusCode.UNAVAILABLE):
            logging.error('grpc unavailable error: %s', e)
            return True
        return False

    @retry(reraise=True, stop=stop_after_attempt(3),
           retry=retry_if_exception(is_grpc_error_unavailable))
    def converse(self):
        """Send a voice request to the Assistant and playback the response.

        Returns: True if conversation should continue.
        """
        continue_conversation = False

        self.conversation_stream.start_recording()
        red_breathing_led.start_breathing()
        logging.info('Recording audio request.')

        def iter_converse_requests():
            for c in self.gen_converse_requests():
                assistant_helpers.log_converse_request_without_audio(c)
                yield c

            self.conversation_stream.start_playback()

        # This generator yields ConverseResponse proto messages
        # received from the gRPC Google Assistant API.
        for resp in self.assistant.Converse(iter_converse_requests(), self.deadline):
            assistant_helpers.log_converse_response_without_audio(resp)
            if resp.error.code != code_pb2.OK:
                logging.error('server error: %s', resp.error.message)
                break
            if resp.event_type == END_OF_UTTERANCE:
                logging.info('End of audio request detected')
                self.conversation_stream.stop_recording()
                red_breathing_led.stop()
            if resp.result.spoken_request_text:
                self.print_spoken_request(resp)
            if len(resp.audio_out.audio_data) > 0:
                self.conversation_stream.write(resp.audio_out.audio_data)
            if resp.result.spoken_response_text:
                self.print_response(resp)
            if resp.result.conversation_state:
                self.conversation_state = resp.result.conversation_state
            if resp.result.volume_percentage != 0:
                self.conversation_stream.volume_percentage = (
                    resp.result.volume_percentage
                )
            if resp.result.microphone_mode == DIALOG_FOLLOW_ON:
                continue_conversation = True
                logging.info('Expecting follow-on query from user.')
            elif resp.result.microphone_mode == CLOSE_MICROPHONE:
                continue_conversation = False
        logging.info('Finished playing assistant response.')
        self.conversation_stream.stop_playback()
        return continue_conversation

    @staticmethod
    def print_spoken_request(resp):
        logging.info('Transcript of user request: "%s".', resp.result.spoken_request_text)
        logging.info('Playing assistant response.')

    @staticmethod
    def print_response(resp):
        logging.info('Transcript of TTS response (only populated from IFTTT): "%s".', resp.result.spoken_response_text)

    def gen_converse_requests(self):
        """Yields: ConverseRequest messages to send to the API."""

        converse_state = None
        if self.conversation_state:
            logging.debug('Sending converse_state: %s',
                          self.conversation_state)
            converse_state = embedded_assistant_pb2.ConverseState(
                conversation_state=self.conversation_state,
            )
        config = embedded_assistant_pb2.ConverseConfig(
            audio_in_config=embedded_assistant_pb2.AudioInConfig(
                encoding='LINEAR16',
                sample_rate_hertz=self.conversation_stream.sample_rate,
            ),
            audio_out_config=embedded_assistant_pb2.AudioOutConfig(
                encoding='LINEAR16',
                sample_rate_hertz=self.conversation_stream.sample_rate,
                volume_percentage=self.conversation_stream.volume_percentage,
            ),
            converse_state=converse_state
        )
        # The first ConverseRequest must contain the ConverseConfig
        # and no audio data.
        yield embedded_assistant_pb2.ConverseRequest(config=config)
        for data in self.conversation_stream:
            # Subsequent requests need audio data, but not config.
            yield embedded_assistant_pb2.ConverseRequest(audio_in=data)


@click.command()
@click.option('--api-endpoint',
              default=ASSISTANT_API_ENDPOINT, metavar='<api endpoint>', show_default=True,
              help='Address of Google Assistant API service.')
@click.option('--credentials',
              metavar='<credentials>', show_default=True,
              default=os.path.join(click.get_app_dir('google-oauthlib-tool'), 'credentials.json'),
              help='Path to read OAuth2 credentials.')
@click.option('--push-gpio-pin', '-pgp',
              metavar='<push gpio pin>', default=PushButton.DEFAULT_GPIO_PIN, show_default=True,
              help='GPIO pin button(GPIO.BCM, GPIO.IN config) that triggers recording')
@click.option('--button-normally-open', '-bno',
              metavar='<button normally open>', default=False, show_default=True, is_flag=True,
              help='Circuit specific ')
@click.option('--verbose', '-v',
              is_flag=True, default=False,
              help='Verbose logging.')
@click.option('--no-boot-sound', '-nbs',
              is_flag=True, default=False,
              help='Do not play boot sound. Takes priority over boot sound option.')
@click.option('--boot-sound', '-bs',
              metavar='<boot sound>', default=BootSound.DEFAULT_BOOT_FILE,
              help='Boot sound to play')
def main(
        push_gpio_pin,
        button_normally_open,
        verbose,
        no_boot_sound,
        boot_sound,
        *args, **kwargs
):
    # Setup logging.
    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO)

    # Button setup
    push_button = PushButton(
        push_gpio_pin,
        button_type=PushButtonType.NO if button_normally_open else PushButtonType.NC,
        verbose=verbose
    )

    # play on boot
    if no_boot_sound:
        logging.info('Not playing boot sound')
    else:
        BootSound(boot_sound).play()

    # Load OAuth 2.0 credentials.
    credentials = os.path.join(click.get_app_dir('google-oauthlib-tool'), 'credentials.json')
    try:
        with open(credentials, 'r') as credential_files:
            credentials = google.oauth2.credentials.Credentials(token=None, **json.load(credential_files))
            http_request = google.auth.transport.requests.Request()
            credentials.refresh(http_request)
    except Exception as e:
        print_credentials_error(e)
        return

    # Create an authorized gRPC channel.
    grpc_channel = google.auth.transport.grpc.secure_authorized_channel(
        credentials, http_request,
        ASSISTANT_API_ENDPOINT
    )
    logging.info('Connecting to %s', ASSISTANT_API_ENDPOINT)

    # Configure audio source and sink.
    audio_device = None
    audio_source = audio_device = (
        audio_device or audio_helpers.SoundDeviceStream(
            sample_rate=audio_helpers.DEFAULT_AUDIO_SAMPLE_RATE,
            sample_width=audio_helpers.DEFAULT_AUDIO_SAMPLE_WIDTH,
            block_size=audio_helpers.DEFAULT_AUDIO_DEVICE_BLOCK_SIZE,
            flush_size=audio_helpers.DEFAULT_AUDIO_DEVICE_FLUSH_SIZE
        )
    )
    audio_sink = audio_device = (
        audio_device or audio_helpers.SoundDeviceStream(
            sample_rate=audio_helpers.DEFAULT_AUDIO_SAMPLE_RATE,
            sample_width=audio_helpers.DEFAULT_AUDIO_SAMPLE_WIDTH,
            block_size=audio_helpers.DEFAULT_AUDIO_DEVICE_BLOCK_SIZE,
            flush_size=audio_helpers.DEFAULT_AUDIO_DEVICE_FLUSH_SIZE
        )
    )
    # Create conversation stream with the given audio source and sink.
    conversation_stream = audio_helpers.ConversationStream(
        source=audio_source,
        sink=audio_sink,
        iter_size=audio_helpers.DEFAULT_AUDIO_ITER_SIZE,
        sample_width=audio_helpers.DEFAULT_AUDIO_SAMPLE_WIDTH,
    )

    with SampleAssistant(conversation_stream, grpc_channel, DEFAULT_GRPC_DEADLINE) as assistant:
        push_button.wait_for_push(trigger_assistant, assistant)


def trigger_assistant(assistant):
    while True:
        if assistant.converse():
            continue
        else:
            break


def print_credentials_error(e):
    logging.error('Error loading credentials: %s', e)
    logging.error('Run google-oauthlib-tool to initialize new OAuth 2.0 credentials.')


if __name__ == '__main__':
    main()
