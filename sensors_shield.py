# ATMegaZero Sensors Shield
#
# You can purchase the ATMegaZero Sensors Shield from the ATMegaZero Online Store at:
# https://shop.atmegazero.com/products/atmegazero-sensors-shield-compatible-with-the-raspberry-pi
#
# For full documentation please visit https://atmegazero.com

import time
import board
import busio
import digitalio
import adafruit_bme280
import adafruit_ds1307
import adafruit_mpu6050
import adafruit_sgp40
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

i2c = busio.I2C(board.SCL, board.SDA)

# BME280 Sensor
bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c)
# change this to match the location's pressure (hPa) at sea level
bme280.sea_level_pressure = 1013.25

# RealTimeClock(RTC)
rtc = adafruit_ds1307.DS1307(i2c)

# Accelerometer
mpu = adafruit_mpu6050.MPU6050(i2c, address=0x69)

# Gass Sensor
sgp = adafruit_sgp40.SGP40(i2c)

# Create analog-to-digital converter
ads = ADS.ADS1115(i2c)
# Create single-ended input on channel 0
chan = AnalogIn(ads, ADS.P0)

class Temperature_Type:
    fahrenheit = 0
    celsius = 1
    def __init__(self, type):
        assert type in ( self.fahrenheit, self.celsius)
        self.selection = type

class ATMegaZero_Sensors_Shield:
    def __init__(self, *args):
        print("Sensors Shield Initialized")
        
    def get_date_time(self):
        t = rtc.datetime
        hour = t.tm_hour % 12
        date_string = "{}/{}/{} - {}:{:02}:{:02}".format(t.tm_mon, t.tm_mday, t.tm_year, hour, t.tm_min, t.tm_sec)
        print("Date/Time: ", date_string)
        return date_string

    def get_current_time_as_tuple(self):
        t = rtc.datetime
        return (t.tm_hour, t.tm_min)

    def get_date_tuple(self):
        t = rtc.datetime
        return (t.tm_mon, t.tm_mday, t.tm_year)

    def get_temperature(self, type = Temperature_Type.fahrenheit):
        if type == Temperature_Type.fahrenheit:
            temperature = bme280.temperature * 9 / 5 + 32
        else:
            temperature = bme280.temperature

        print("Temperature: ", str(temperature))
        return temperature

    def get_barometric_pressure(self):
        barometric_pressure = "%0.1f hPa" % bme280.pressure
        print("Barometric Pressure: ", barometric_pressure)
        return barometric_pressure

    def get_altitude(self):
        altitude = "%0.2f meters" % bme280.altitude
        print("Altitude: ", altitude)
        return altitude
    
    def get_humidity(self):
        humidity = bme280.relative_humidity
        print("Humidity: ", str(humidity))
        return humidity

    def get_accelerometer(self):
        acceleration = "X:%.2f, Y: %.2f, Z: %.2f m/s^2" % (mpu.acceleration)
        print("Acceleration: ", acceleration)
        return acceleration
    
    def get_gyroscope(self):
        gyro = "X:%.2f, Y: %.2f, Z: %.2f degrees/s" % (mpu.gyro)
        print("Gyro: ", gyro)
        return gyro

    def get_raw_gass_value(self):
        raw_gass = sgp.raw
        print("Raw Gas: ", raw_gass)
        return raw_gass

    def get_light_sensor_value(self):
        print("{:>5}\t{:>5.3f}".format(chan.value, chan.voltage))
        brightness = chan.value / 1000
        print("brightness: ", brightness)
        return brightness

    def set_date_time(self):
            # year, mon, date, hour, min, sec, wday, yday, isdst
        t = time.struct_time((2021, 04, 7, 19, 46, 0, 2, -1, -1))
        # you must set year, mon, date, hour, min, sec and weekday
        # yearday is not supported, isdst can be set but we don't do anything with it at this time
        print("Setting time to:", t)  # uncomment for debugging
        rtc.datetime = t