# ATMegaZero Garage Automation

# With this project you can automate a two car garage and control it remotely using adafruit.io dashboard.
# This project was design to use the following ATMegaZero boards:
#   - The ATMegaZero ESP32-S2 (coming soon)
#   - The ATMegaZero Relay Shield
#   - The ATMegaZero Sensors Shield
#   - The ATMegaZero Learning Shield
# You can find some of these shields on https://shop.atmegazero.com
# You will also need to create an account on https://io.adafruit.com and setup the appropriate feeds.

# Created by: Eddie Espinal (@4hackrr)
# For full documentation please visit https://atmegazero.com

from garage_manager import Garage_Manager, LED, Relay

garageManager = Garage_Manager()
    
def loop():
    while True:
        garageManager.loop()    
        
if __name__ == '__main__':
    loop()
