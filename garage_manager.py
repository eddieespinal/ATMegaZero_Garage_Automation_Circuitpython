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

import sys
import time
import board
import busio
from digitalio import DigitalInOut, Pull, Direction
import neopixel

import ssl
import socketpool
import wifi
import adafruit_minimqtt.adafruit_minimqtt as MQTT
from adafruit_io.adafruit_io import IO_HTTP, AdafruitIO_RequestError

from sensors_shield import ATMegaZero_Sensors_Shield as SensorsShield, Temperature_Type
from learning_shield import ATMegaZero_Learning_Shield as LearningShield, LED
from relay_shield import ATMegaZero_Relay_Shield as RelayShield, Relay
from adafruit_io_helper import AdafruitIOHelper

import adafruit_sdcard
import storage
import supervisor

try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

aio_username = secrets["aio_username"]
aio_key = secrets["aio_key"]

# Relays Feed
door1button_feed = secrets["aio_username"] + "/feeds/garagegroup.door1button"
door2button_feed = secrets["aio_username"] + "/feeds/garagegroup.door2button"
relay3_feed = secrets["aio_username"] + "/feeds/garagegroup.relay3"
relay4_feed = secrets["aio_username"] + "/feeds/garagegroup.relay4"

# Status Feed
door1status_feed = secrets["aio_username"] + "/feeds/garagegroup.door1status"
door2status_feed = secrets["aio_username"] + "/feeds/garagegroup.door2status"

# Auto close doors switch Feed
auto_close_doors_feed = secrets["aio_username"] + "/feeds/garagegroup.auto-close-doors"

# Sensors Feed
temperature_feed = secrets["aio_username"] + "/feeds/garagegroup.temperature"
humidity_feed = secrets["aio_username"] + "/feeds/garagegroup.humidity"
hpa_feed = secrets["aio_username"] + "/feeds/garagegroup.hpa"
brightness_feed = secrets["aio_username"] + "/feeds/garagegroup.brightness"
raw_gas_feed = secrets["aio_username"] + "/feeds/garagegroup.gas"

# Connect to the SD Card and mount the filesystem.
SD_CS = board.SD_CS
spi = busio.SPI(board.SCK, board.MISO, board.MOSI)
cs = DigitalInOut(SD_CS)
sdcard = adafruit_sdcard.SDCard(spi, cs)
vfs = storage.VfsFat(sdcard)
storage.mount(vfs, "/sd")

LOG_FILE = "atmegazero_logs.txt"

# This will help not send too many request too fast to adafruit.io
PUBLISH_TIME_INTERVAL = 60 # every 60 seconds

# Close garage automatically at 11:30pm
AUTO_CLOSE_DOORS_AFTER_HOUR = 23 # 11PM in 24hr format
AUTO_CLOSE_DOORS_AFTER_MINUTES = 30
AUTO_CLOSE_WAIT_TIME_IN_MINUTES = 30 * 60 # 30 mins wait time before trying to auto close doors again.

# Door1 Magnetic Switch Sensors
door1_magnetic_sensor = DigitalInOut(board.D10)
door1_magnetic_sensor.direction = Direction.INPUT
door1_magnetic_sensor.pull = Pull.UP

# Door2 Magnetic Switch Sensors
door2_magnetic_sensor = DigitalInOut(board.D9)
door2_magnetic_sensor.direction = Direction.INPUT
door2_magnetic_sensor.pull = Pull.UP

class Garage_Manager:
    def __init__(self, *args):
        self.sensors_shield = SensorsShield()
        self.learning_shield = LearningShield()
        self.relay_shield = RelayShield()

        # let's turn on the Yellow LED while we initialize the board and connect to the internet and mqtt
        self.learning_shield.turn_led_on(LED.yellow)

        self.pixel = neopixel.NeoPixel(board.NEOPIXEL, 1, pixel_order=neopixel.RGB)
        self.last_published_time = 0
        self.is_automatically_closing_garage_doors = False
        self.automatically_closed_datetime_tuple = None
        self.last_auto_close_time = 0
        
        self.connect_to_wifi()
        self.connect_to_mqtt()
        
        # get the default values from adafruit io
        self.set_default_values()

        # turn off the Yellow LED to indicate we are done initializing
        self.learning_shield.turn_led_off(LED.yellow)

        # make an audiable signal that we are done initializing
        self.learning_shield.beep_by(2, delay = 0.25)

        self.door1_is_opened = False
        self.door2_is_opened = False

        self.log_to_sd_card("Initialized")

        # Start a blocking loop to check for new messages
        self.loop()

    def loop(self):
        try:
            self.mqtt_client.loop()
        except Exception as e:
            print("Failed to get data, retrying\n", e)
            self.log_to_sd_card("Failed while running the mqtt_client_loop() inside loop() function")
            self.learning_shield.turn_led_on(LED.red)
            self.reconnect()
            return

        # Publish data every x seconds
        current_time = time.monotonic()
        if (current_time - self.last_published_time) >= PUBLISH_TIME_INTERVAL:
            print("Time to publish events")
            self.publish_sensor_data()

        # Check the status of the door sensors
        self.check_garage_safety_sensor_status()

        # Check if the garage doors are opened past the designated time and try to automatically close them
        if not self.is_automatically_closing_garage_doors and self.can_close_doors_automatically():
            self.close_garage_doors_if_necessary()
        
    def set_default_values(self):
        try:
            self.adafruit_io_helper = AdafruitIOHelper(aio_key, self.pool, self.ssl_context)
            if self.adafruit_io_helper.get_last_value_for_feed(auto_close_doors_feed) == "ON": 
                self.enable_close_doors_automatically = True
            else: 
                self.enable_close_doors_automatically = False
        except:
            print("Issue setting default values")
            pass

    def toggle_relay(self, relay, shouldBuzz):
        self.relay_shield.toggle_relay(relay)

        self.pixel[0] = (0, 0, 255)
        self.learning_shield.turn_led_on(LED.yellow)

        if shouldBuzz:
            self.learning_shield.beep()

    def open_or_close_door(self, relay, shouldBuzz = False):
        self.learning_shield.turn_led_on(LED.green)
        self.toggle_relay(relay, shouldBuzz)

    def reset_status(self):
        self.learning_shield.turn_led_off(LED.yellow)
        self.learning_shield.turn_led_off(LED.red)
        self.learning_shield.turn_led_off(LED.green)

        self.pixel[0] = (0, 0, 0)
        self.relay_shield.reset()

    def connect_to_wifi(self):
        try:
            print("Connecting to %s" % secrets["ssid"])
            wifi.radio.connect(secrets["ssid"], secrets["password"])
            print("Connected to %s!" % secrets["ssid"])
            print("my IP addr:", wifi.radio.ipv4_address)
        except:
            print("Error connnecting to Wifi")
            self.log_to_sd_card("Error connnecting to Wifi")
            self.reset_status()
            self.learning_shield.turn_led_on(LED.red)
            time.sleep(60)
            self.reconnect()
            pass

    def reconnect(self):
        print("Reconnecting  - Performing soft reboot")
        # Let's soft reboot the board to clear everything out and prevent error with socket.
        self.log_to_sd_card("Performing soft reboot to recover from broken connections.")
        supervisor.reload()
        

    def connect_to_mqtt(self):
        print("Connecting to MQTT Server")

        # Create a socket pool
        self.pool = socketpool.SocketPool(wifi.radio)
        self.ssl_context = ssl.create_default_context()

        # Set up a MiniMQTT Client
        self.mqtt_client = MQTT.MQTT(
            broker=secrets["broker"],
            port=secrets["port"],
            username=secrets["aio_username"],
            password=secrets["aio_key"],
            socket_pool=self.pool,
            ssl_context=self.ssl_context,
        )

        # Setup the callback methods above
        self.mqtt_client.on_connect = self.connected
        self.mqtt_client.on_disconnect = self.disconnected
        self.mqtt_client.on_message = self.message
        self.mqtt_client.on_subscribe = self.subscribe

        # Connect the client to the MQTT broker.
        print("Connecting to Adafruit IO...")
        try:
            self.mqtt_client.connect()
        except Exception as e:
            print(e)
            self.log_to_sd_card("Something went wrong connecting to MQTT server")
            time.sleep(60)
            self.reconnect()
            # failing gracefully for now since we can try again in the next cycle
            pass

    def publish_sensor_data(self):
        brightness = self.sensors_shield.get_light_sensor_value()
        temp = self.sensors_shield.get_temperature()
        humidity = self.sensors_shield.get_humidity()
        hpa = self.sensors_shield.get_barometric_pressure()
        raw_gas = self.sensors_shield.get_raw_gass_value()

        print("Sending values")
        try:
            self.mqtt_client.publish(temperature_feed, temp)
            self.mqtt_client.publish(humidity_feed, humidity)
            self.mqtt_client.publish(hpa_feed, hpa)
            self.mqtt_client.publish(brightness_feed, brightness)
            self.mqtt_client.publish(raw_gas_feed, raw_gas)
        except:
            print("Something went wrong sending data to MQTT")
            self.log_to_sd_card("Error while sending data to MQTT Broker")
            # failing gracefully for now since we can try again in the next cycle
            return 

        self.publish_door_status(door1status_feed, int(door1_magnetic_sensor.value))
        self.publish_door_status(door2status_feed, int(door2_magnetic_sensor.value))

        # save the last time we published data
        current_time = time.monotonic()
        self.last_published_time = current_time
    
    def publish_door_status(self, door_feed, value):
        print("publishing door status:", door_feed)
        try:
            self.mqtt_client.publish(door_feed, value)
        except:
            print("Something went wrong sending data to MQTT")
            # failing gracefully for now since we can try again in the next cycle
            pass

    def connected(self, client, userdata, flags, rc):
        # This function will be called when the client is connected
        # successfully to the broker.
        print("Connected to Adafruit IO!")
        # Subscribe to the relay feeds
        client.subscribe(door1button_feed)
        client.subscribe(door2button_feed)
        client.subscribe(relay3_feed)
        client.subscribe(relay4_feed)
        client.subscribe(auto_close_doors_feed)

    def disconnected(self, client, userdata, rc):
        # This method is called when the client is disconnected
        print("Disconnected from Adafruit IO!")

    def subscribe(self, client, userdata, topic, granted_qos):
        # This method is called when the client subscribes to a new feed.
        print("Subscribed to {0}".format(topic))

    def message(self, client, topic, message):
        # This method is called when a topic the client is subscribed to
        # has a new message.
        print("New message on topic {0}: {1}".format(topic, message))
        if topic == door1button_feed:
            if message == "OPEN":
                print("Turning relay #1 ON")
                self.open_or_close_door(Relay.one, shouldBuzz=False)
            elif message == "CLOSE":
                print("Turning relay #1 OFF")
                self.open_or_close_door(Relay.one, shouldBuzz=False)
        elif topic == door2button_feed:
            if message == "OPEN":
                print("Turning relay #2 ON")
                self.open_or_close_door(Relay.two, shouldBuzz=False)
            elif message == "CLOSE":
                print("Turning relay #2 OFF")
                self.open_or_close_door(Relay.two, shouldBuzz=False)
        elif topic == relay3_feed:
            print("Got a message for relay3", message)
        elif topic == relay4_feed:
            print("Got a message for relay4", message)
        elif topic == auto_close_doors_feed:
            if message == "ON":
                self.enable_close_doors_automatically = True
            else:
                self.enable_close_doors_automatically = False
        else:
            print("Got a message that doesn't match any topics")

        self.reset_status()

    def log_to_sd_card(self, message):
        try:
            # open file for append
            with open(f"/sd/{LOG_FILE}", "a") as f:
                date_time = self.sensors_shield.get_date_time()
                log_string = f"{date_time} - {message}\n"
                f.write(log_string)
                print(log_string)
            # file is saved
            time.sleep(1)
        except:
            print("Error logging to SD Card")
            pass

    def can_close_doors_automatically(self):
        now = time.monotonic()
        if now - self.last_auto_close_time >= AUTO_CLOSE_WAIT_TIME_IN_MINUTES:
            return True
        
        return False

    def close_garage_doors_if_necessary(self):
        if not self.enable_close_doors_automatically:
            return

        hour, minutes = self.sensors_shield.get_current_time_as_tuple()

        if hour == AUTO_CLOSE_DOORS_AFTER_HOUR and minutes >= AUTO_CLOSE_DOORS_AFTER_MINUTES:
            print("We should try to close the garage automatically")
            self.is_automatically_closing_garage_doors = True
            self.automatically_closed_datetime_tuple = self.sensors_shield.get_date_tuple() + self.sensors_shield.get_current_time_as_tuple()
            self.last_auto_close_time = time.monotonic()

            self.log_to_sd_card("About to close garage doors automatically")

            # First check the door status to see which door is opened
            door_opened_relays = []
            if self.door1_is_opened:
                print("Door one is opened, adding it to the array")
                door_opened_relays.append(Relay.one)
            
            if self.door2_is_opened:
                print("Door two is opened, adding it to the array")
                door_opened_relays.append(Relay.two)

            print(door_opened_relays)
            if len(door_opened_relays) > 0:
                # We have open door(S)
                print("We have doors opened, let's try to close them.")

                # Beep a few times before sending the close command
                self.learning_shield.beep_by(5, 1.0)
                time.sleep(15)

                # Run the mqtt loop to make sure we don't have new events before closing the garage. 
                # This is an opportunity to stop this process from adafruit.io dashboard.
                try:
                    self.mqtt_client.loop()
                except Exception as e:
                    print("Failed to run the mqtt_client_loop()\n", e)
                    self.log_to_sd_card("Failed to run the mqtt_client_loop() from close_garage_doors_if_necessary()")
                    pass

                if not self.enable_close_doors_automatically:
                    return

                time.sleep(5)
                self.learning_shield.beep_by(10, 0.10)

                time.sleep(1)
                # We are good to close the doors now
                for relay in door_opened_relays:
                    self.log_to_sd_card(f"Closing Door #{relay}")
                    self.learning_shield.beep_by(3, 0.20)
                    self.open_or_close_door(relay)
                    time.sleep(5)
                
                self.reset_status()
                self.is_automatically_closing_garage_doors = False

            # Check door status to confirm is closed
            self.check_garage_safety_sensor_status()

            # Publish door status to adafruit.io dashboard
            self.publish_sensor_data()
        
    def check_garage_safety_sensor_status(self):
        if door1_magnetic_sensor.value:
            self.door1_is_opened = True
            self.learning_shield.turn_led_on(LED.red)
            self.learning_shield.turn_led_off(LED.green)
            time.sleep(1)
        else:
            self.door1_is_opened = False
            self.learning_shield.turn_led_off(LED.red)
            self.learning_shield.turn_led_on(LED.green)
            time.sleep(1)

        # Check Door #2
        if door2_magnetic_sensor.value:
            self.door2_is_opened = True
            self.learning_shield.turn_led_on(LED.yellow)
            time.sleep(1)
        else:
            self.door2_is_opened = False
            self.learning_shield.turn_led_off(LED.yellow)
            time.sleep(1)
