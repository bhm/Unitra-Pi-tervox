import RPi.GPIO as GPIO
from time import sleep
from enum import Enum
import logging

DEFAULT_SLEEP_TIME = 0.05


class PushButtonType(Enum):
    NC = 1  # normally CLOSED
    NO = 2  # normally OPEN

    def is_triggered(self, gpio_high):
        return (self == PushButtonType.NC and gpio_high) or \
               (self == PushButtonType.NO and not gpio_high)


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

    def wait_for_push(self, do_on_push, **kwargs):
        if not self.gpio_inited:
            self.init_gpio()

        while True:
            gpio_is_high = GPIO.input(self.button_gpio_pin)

            if self.button_type.is_triggered(gpio_is_high):
                self.__trigger(do_on_push, **kwargs)

            sleep(self.sleep_time)

    def __trigger(self, do_on_push, **kwargs):
        if do_on_push is not None:
            logging.debug('Push button at %s activated' % self.button_gpio_pin)
            do_on_push(**kwargs)

    def init_gpio(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(self.verbose)
        GPIO.setup(self.button_gpio_pin, GPIO.IN)
        self.gpio_inited = True
        return
