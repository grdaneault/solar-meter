from influx import InfluxDB
import requests
import json
from datetime import datetime

INFLUX_HOST = '192.168.1.215'
INFLUX_PORT = 8086
INFLUX_DATABASE = 'solar'

# This creates the client instance... subsequent calls with the same URL will
# return the exact same instance, allowing you to use socket pooling for faster
# requests with less resources.
client = InfluxDB('http://%s:%s' % (INFLUX_HOST, INFLUX_PORT))

# You can write as many fields and tags as you like, or override the *time* for
# the data points


def record_data(measurement, value, type, read_time):
    client.write(INFLUX_DATABASE, measurement,
                 fields={'value': value},
                 tags={'type': type},
                 time=read_time)


resp = requests.get('http://192.168.1.92/production.json?details=1')
print(json.dumps(resp.json(), indent=2))

d = resp.json()

inverterStats = d['production'][0]
read_time = datetime.fromtimestamp(inverterStats['readingTime'])

record_data('wattHours', inverterStats['wNow'], type='inverters', read_time=read_time)
record_data('activePanels', inverterStats['activeCount'], type='inverters', read_time=read_time)
record_data('totalGeneration', inverterStats['whLifetime'], type='inverters', read_time=read_time)

eimStats = d['production'][1]
read_time = datetime.fromtimestamp(eimStats['readingTime'])
record_data('wattHours', eimStats['wNow'], type='eim', read_time=read_time)
record_data('wattHours', eimStats['whLifetime'], type='eim', read_time=read_time)
