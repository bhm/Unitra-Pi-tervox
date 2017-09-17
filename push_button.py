import RPi.GPIO as GPIO
from time import sleep
from enum import Enum
import logging

DEFAULT_SLEEP_TIME = 0.05


class PushButtonType(Enum):
    NC = 1  # normally CLOSED
    NO = 2  # normally OPEN


class PushButton(object):
    DEFAULT_GPIO_PIN = 14

    def __init__(
            self,
            pin=DEFAULT_GPIO_PIN,
            button_type=PushButtonType.NC,
            sleep_time=DEFAULT_SLEEP_TIME,
            verbose=False
    ):
        self.sleep_time = sleep_time
        self.button_gpio_pin = pin
        self.button_type = button_type
        self.gpio_inited = False
        self.verbose = verbose
        logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO)

    def wait_for_push(self, do_on_push, do_on_push_args):
        if not self.gpio_inited:
            self.init_gpio()

        while True:
            gpio_high = GPIO.input(self.button_gpio_pin)

            if self.button_type is PushButtonType.NC and gpio_high:
                self.trigger_push(do_on_push, do_on_push_args)
            elif self.button_type is PushButtonType.NO and not gpio_high:
                self.trigger_push(do_on_push, do_on_push_args)

            sleep(self.sleep_time)

    def trigger_push(self, do_on_push, do_on_push_args):
        logging.debug('Push button at %s activated' % self.button_gpio_pin)
        if do_on_push is not None:
            do_on_push(do_on_push_args)

    def init_gpio(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(self.verbose)
        GPIO.setup(self.button_gpio_pin, GPIO.IN)
        self.gpio_inited = True
        return
