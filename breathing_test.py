from breathing_led import BreathingLed
from time import sleep
import RPi.GPIO as GPIO

YELLOW_PIN = 18
RED_PIN = 23
GREEN_PIN = 24


class LEDArray(object):
    def __init__(self, leds):
        self.leds = leds

    def __enter__(self):
        GPIO.cleanup()

    def start(self):
        for led in self.leds:
            led.start_breathing()
            sleep(0.2)

    def __exit__(self, exc_type, exc_val, exc_tb):
        GPIO.cleanup()


if __name__ == '__main__':
    array = LEDArray(
        {
            BreathingLed(led_pin=YELLOW_PIN),
            BreathingLed(led_pin=RED_PIN),
            BreathingLed(led_pin=GREEN_PIN)
        }
    )
    array.start()
