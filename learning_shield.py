# ATMegaZero Learning Shield
#
# You can purchase the ATMegaZero Learning Shield from the ATMegaZero Online Store at:
# https://shop.atmegazero.com/products/atmegazero-learning-shield
#
# For full documentation please visit https://atmegazero.com

import board
import time
from digitalio import DigitalInOut, Pull

class LED:
    red = 0
    yellow = 1
    green = 2
    def __init__(self, led):
        assert led in (self.red, self.yellow, self.green)
        self.selection = led

class ATMegaZero_Learning_Shield:
    def __init__(self, *args):
        print("Learning Shield Initialized")
        # LEDs
        self.redLED = DigitalInOut(board.A0)
        self.redLED.switch_to_output()
        self.greenLED = DigitalInOut(board.A2)
        self.greenLED.switch_to_output()
        self.yellowLED = DigitalInOut(board.A1)
        self.yellowLED.switch_to_output()
        self.buzzer = DigitalInOut(board.D6)
        self.buzzer.switch_to_output()

        # Push Button
        self.pushButton = DigitalInOut(board.D7)
        self.pushButton.switch_to_input(pull=Pull.DOWN)

    def turn_led_on(self, led):
        if led == LED.red:
            self.redLED.value = True
        elif led == LED.yellow:
            self.yellowLED.value = True
        elif led == LED.green:
            self.greenLED.value = True

    def turn_led_off(self, led):
        if led == LED.red:
            self.redLED.value = False
        elif led == LED.yellow:
            self.yellowLED.value = False
        elif led == LED.green:
            self.greenLED.value = False
 
    def beep(self):
        self.buzzer.value = True
        time.sleep(0.1)
        self.buzzer.value = False

    def beep_by(self, numOfBeeps, delay = 0.5):
        for _ in range(numOfBeeps):
            self.buzzer.value = True
            time.sleep(delay)
            self.buzzer.value = False
            time.sleep(delay)
    