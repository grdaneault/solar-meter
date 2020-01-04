from influx import InfluxDB
import paho.mqtt.client as mqtt
import logging
import requests
from datetime import datetime
import time
import os

logger = logging.getLogger('data_loader')
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler()
# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

INFLUX_HOST = os.getenv('INFLUX_HOST', '192.168.1.215')
INFLUX_PORT = 8086
INFLUX_DATABASE = 'solar'
MQTT_HOST = os.getenv('MQTT_HOST', '192.168.1.215')

logger.info("Data Loader starting...")
# This creates the client instance... subsequent calls with the same URL will
# return the exact same instance, allowing you to use socket pooling for faster
# requests with less resources.

def make_influx_connection(url):
    for i in range(20):
        try:   
            client = InfluxDB(url)
            client.show_tags(database='solar', measurement='totalGeneration')
            return client
        except Exception as e:
            logger.warning("Failed connecting to influxDB on " + url + " (attempt " + str(i + 1) + ")")
            logger.warning("Exception details: " + str(e)) 
            time.sleep(10)
    raise ValueError("Aborting influx connection after 20 attempts")


influx_client = make_influx_connection('http://%s:%s' % (INFLUX_HOST, INFLUX_PORT))
mqtt_client = mqtt.Client()

def on_connect(client, userdata, flags, rc):
    logger.info("Connected to MQTT on %s. result code: %s" % (MQTT_HOST, rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe("/sensor/temp")
    client.subscribe("/sensor/humidity")


def on_message(client, userdata, msg):
    val = float(msg.payload)
    metric = None
    if msg.topic == "/sensor/temp":
        metric = "sensor.temp"
    elif msg.topic == "/sensor/humidity":
        metric = "sensor.humidity"
    else:
        return

    logger.info("received %s reading: %d" % (metric, val))

    influx_client.write(INFLUX_DATABASE, metric,
                        fields={'value': val},
                        time=datetime.fromtimestamp(time.time()))


def record_data(measurement, value, type, read_time):
    influx_client.write(INFLUX_DATABASE, measurement,
                        fields={'value': value},
                        tags={'type': type},
                        time=read_time)
    mqtt_client.publish('/solar/%s/%s' % (type, measurement), value)


def get_solar_data():
    logger.debug('Fetching solar data... ')
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



if __name__ == '__main__':
    logger.info("Ready to collect solar data!")
    mqtt_client.on_message = on_message
    mqtt_client.on_connect = on_connect

    mqtt_client.connect(MQTT_HOST, 1883, 60)
    mqtt_client.loop_start()

    while True:
        get_solar_data()
        mqtt_client.loop()
        time.sleep(15)


