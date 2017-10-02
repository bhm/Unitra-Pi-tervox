import RPi.GPIO as GPIO
from time import sleep
import threading
import logging

ONE_SECOND_IN_MILLIS = 1000


class BreathingLed(object):
    def __init__(self, led_pin=12, hertz=200, cycle_time=2):
        logging.basicConfig(level=logging.DEBUG)
        self.led_with_pwm_setup = None
        self.setup_done = False
        self.keep_breathing = False
        self.process = None
        self.hertz = hertz
        self.sleep_time = ((cycle_time * ONE_SECOND_IN_MILLIS) / (hertz * 2)) / ONE_SECOND_IN_MILLIS
        logging.info('sleep time %s' % self.sleep_time)
        self.led_pin = led_pin

    def start_breathing(self):
        if self.process is None:
            self.keep_breathing = True
            self.process = threading.Thread(target=self.__breath)
            self.process.start()

    def __breath(self):
        if self.led_with_pwm_setup is None:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.led_pin, GPIO.OUT)
            self.led_with_pwm_setup = GPIO.PWM(self.led_pin, self.hertz)

        self.led_with_pwm_setup.start(0)
        try:
            while True:
                if not self.keep_breathing:
                    self.stop()
                    return

                self.__breathe_in_out()

        except KeyboardInterrupt:
            self.stop()
            GPIO.cleanup()
            return

    def __breathe_in_out(self):
        for i in range(0, 101, 5):
            self.led_with_pwm_setup.ChangeDutyCycle(i)
            sleep(0.1)

        for i in range(100, -1, -5):
            self.led_with_pwm_setup.ChangeDutyCycle(i)
            sleep(0.1)

    def stop(self):
        try:
            self.keep_breathing = False
        finally:
            self.process = None
        exit(0)

    def __exit__(self, exc_type, exc_val, exc_tb):
        GPIO.cleanup()
