import RPi.GPIO as GPIO
from time import sleep
from enum import Enum

DEFAULT_SLEEP_TIME = 0.05


class PushButtonType(Enum):
    NC = 1  # normally CLOSED
    NO = 2  # normally OPEN


class PushButton(object):
    def __init__(self, pin=14, button_type=PushButtonType.NC, sleep_time=DEFAULT_SLEEP_TIME):
        self.sleep_time = sleep_time
        self.button_gpio_pin = pin
        self.button_type = button_type
        self.gpio_inited = False

    def wait_for_push(self, do_on_push, do_on_push_args):
        if not self.gpio_inited:
            self.init_gpio()

        while True:
            if GPIO.input(self.button_gpio_pin):
                print('Push button at %s activated' % self.button_gpio_pin)
                if do_on_push is not None:
                    do_on_push(do_on_push_args)

            sleep(self.sleep_time)

    def init_gpio(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(True)
        GPIO.setup(self.button_gpio_pin, GPIO.IN)
        self.gpio_inited = True
        return
