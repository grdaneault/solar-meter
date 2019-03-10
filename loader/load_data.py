from influx import InfluxDB
import paho.mqtt.client as mqtt

import requests
from datetime import datetime
import time
import os

INFLUX_HOST = os.getenv('INFLUX_HOST', '192.168.1.215')
INFLUX_PORT = 8086
INFLUX_DATABASE = 'solar'
MQTT_HOST = os.getenv('MQTT_HOST', '192.168.1.215')

print("Data Loader starting...")
# This creates the client instance... subsequent calls with the same URL will
# return the exact same instance, allowing you to use socket pooling for faster
# requests with less resources.
influx_client = InfluxDB('http://%s:%s' % (INFLUX_HOST, INFLUX_PORT))
print("Connected to InfluxDB on " + INFLUX_HOST)

mqtt_client = mqtt.Client()
mqtt_client.connect(MQTT_HOST, 1883, 60)
print("Connected to MQTT on " + MQTT_HOST)

mqtt_client.loop_start()


def record_data(measurement, value, type, read_time):
    influx_client.write(INFLUX_DATABASE, measurement,
                        fields={'value': value},
                        tags={'type': type},
                        time=read_time)
    mqtt_client.publish('/solar/%s/%s' % (type, measurement), value)


def get_solar_data():
    print('Fetching solar data... ', end='')
    resp = requests.get('http://192.168.1.92/production.json?details=1')
    d = resp.json()

    inverter_stats = d['production'][0]
    read_time = datetime.fromtimestamp(inverter_stats['readingTime'])

    record_data('wattHours', inverter_stats['wNow'], type='inverters', read_time=read_time)
    record_data('activePanels', inverter_stats['activeCount'], type='inverters', read_time=read_time)
    record_data('totalGeneration', inverter_stats['whLifetime'], type='inverters', read_time=read_time)

    eim_stats = d['production'][1]
    read_time = datetime.fromtimestamp(eim_stats['readingTime'])
    record_data('wattHours', eim_stats['wNow'], type='eim', read_time=read_time)
    record_data('totalGeneration', eim_stats['whLifetime'], type='eim', read_time=read_time)

    for metric in ['varhLeadLifetime', 'varhLagLifetime', 'vahLifetime', 'rmsCurrent', 'rmsVoltage', 'reactPwr', 'apprntPwr', 'pwrFactor', 'whToday', 'whLastSevenDays', 'vahToday', 'varhLeadToday', 'varhLagToday']:
        record_data(metric, eim_stats[metric], type='eim', read_time=read_time)

    print('done.')


if __name__ == '__main__':
    print("Ready to collect solar data!")
    while True:
        get_solar_data()
        time.sleep(30)

