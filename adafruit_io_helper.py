# Adafruit IO
#
# This class allows you to get the last value from a feed without using mqtt.
#
# Created by: Eddie Espinal
# For full documentation please visit https://io.adafruit.com

import adafruit_requests as requests

ADAFRUIT_IO_API_URL = "https://io.adafruit.com/api/v2/{}/?X-AIO-Key={}"

class AdafruitIOHelper:
    def __init__(self, aio_key, pool, ssl_context, *args):
        print("AdafruitIOHelper Initilized")
        self.aio_key = aio_key
        self.pool = pool
        self.context = ssl_context
        self.request = requests.Session(self.pool, self.context)
        
    def get_last_value_for_feed(self, feed):
        feed_url = self.get_api_url_for_feed(feed)
        response = self.request.get(feed_url)
        json = response.json()
        response.close()
        last_value = json["last_value"]
        return last_value

    def get_api_url_for_feed(self, feed):
        url = ADAFRUIT_IO_API_URL.format(feed, self.aio_key)
        return url