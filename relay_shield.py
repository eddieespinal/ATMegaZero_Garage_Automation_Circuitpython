# ATMegaZero Relay Shield
#
# You can purchase the ATMegaZero Relay Shield from the ATMegaZero Online Store at:
# https://shop.atmegazero.com
#
# For full documentation please visit https://atmegazero.com

import time
import board
from digitalio import DigitalInOut, Pull

class Relay:
    one = 0
    two = 1
    three = 2
    four = 3
    def __init__(self, relay):
        assert relay in (self.one, self.two, self.three, self.four)
        self.selection = relay

class ATMegaZero_Relay_Shield:
    def __init__(self, *args):
        print("Relay Shield Initialized")
        # Set up a pin for controlling the relays
        self.relay1 = DigitalInOut(board.IO5)
        self.relay1.switch_to_output()
        self.relay2 = DigitalInOut(board.D8)
        self.relay2.switch_to_output()
        self.relay3 = DigitalInOut(board.D12)
        self.relay3.switch_to_output()
        self.relay4 = DigitalInOut(board.D13)
        self.relay4.switch_to_output()

        self.reset()
        
    def toggle_relay(self, relay):
        if relay == Relay.one:
            self.relay1.value = False
        elif relay == Relay.two:
            self.relay2.value = False
        elif relay == Relay.three:
            self.relay3.value = False
        elif relay == Relay.four:
            self.relay4.value = False
        time.sleep(0.5)
        self.reset()

    def reset(self):
        self.relay1.value = True
        self.relay2.value = True
        self.relay3.value = True
        self.relay4.value = True