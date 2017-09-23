
import RPi.GPIO as GPIO
from time import sleep
import threading


class BreathingLed(object):
    def __init__(self, led_pin=12, hertz=100, cycle_time=1):
        self.led = None
        self.hertz = hertz
        self.sleep_time = (cycle_time * 1000) / (hertz * 2)
        self.led_pin = led_pin
        self.setup_done = False
        self.keep_breathing = False
        self.process = None

    def start_breathing(self):
        if self.process is None:
            self.keep_breathing = True
            self.process = threading.Thread(target=self.__breath)
            self.process.start()

    def __breath(self):
        if self.led is None:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.led_pin, GPIO.OUT)
            self.led = GPIO.PWM(self.led_pin, self.hertz)

        self.led.start(0)
        try:
            while True:
                if not self.keep_breathing:
                    self.stop()
                    return
                for i in range(0, self.hertz + 1, 1):
                    self.led.ChangeDutyCycle(i)
                    sleep(self.sleep_time)
                for i in range(self.hertz, -1, -1):
                    self.led.ChangeDutyCycle(i)
                    sleep(self.sleep_time)

        except KeyboardInterrupt:
            self.stop()
            return

    def stop(self):
        try:
            self.keep_breathing = False
        finally:
            self.process = None

    def __exit__(self, exc_type, exc_val, exc_tb):
        GPIO.cleanup()
