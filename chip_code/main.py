import math
import time
import machine
import dht
from umqtt.robust import MQTTClient
from config import MQTT_HOST


class SolarMeter(object):
    def __init__(self, mqtt_host, meter_pin, dht_pin, led_pin):
        meter_pin = machine.Pin(meter_pin, machine.Pin.OUT)
        self.meter_pwm = machine.PWM(meter_pin, freq=1000)

        dht_pin = machine.Pin(dht_pin, machine.Pin.IN)
        self.dht = dht.DHT11(dht_pin)

        led_pin = machine.Pin(led_pin, machine.Pin.OUT)
        self.led_pwm = machine.PWM(led_pin, freq=1000)

        self.curr_power = 0
        self.max_power = 4500

        self.mqtt = None
        self.init_mqtt(mqtt_host)

    def init_mqtt(self, mqtt_host):
        self.mqtt = MQTTClient("solar-meter", mqtt_host)
        self.mqtt.DEBUG = True
        self.mqtt.set_callback(self.on_topic_notification)

        if not self.mqtt.connect(clean_session=False):
            print("New session being set up")

        self.mqtt.subscribe(b"/solar/eim/wattHours")
        self.mqtt.subscribe(b"/solar/meta/maxWattHours")

    def on_topic_notification(self, topic, data):
        if topic == b"/solar/eim/wattHours":
            print("Updating current power...", end=' ')
            self.curr_power = float(data.decode('utf-8'))
        elif topic == b"/sensor/meta/maxWattHours":
            print("Updating max power...", end=' ')
            self.max_power = float(data.decode('utf-8'))
        else:
            print("Unexpected topic!", topic)

        self.update_meter()
        print('{"current power": %d, "max power": %d}' % (self.curr_power, self.max_power))

    def pulse(self, pwm, interval):
        for i in range(20):
            pwm.duty(int(math.sin(i / 10 * math.pi) * 500 + 500))
            time.sleep_ms(interval)

    def update_meter(self):
        val = int(self.curr_power / self.max_power * 1024)
        val = min(max(val, 0), 1023)
        self.meter_pwm.duty(val)

    def publish_dht(self):
        self.dht.measure()
        temp = self.dht.temperature()
        humidity = self.dht.humidity()
        print("Recorded Temp: %d C, Humidity: %d" % (temp, humidity))
        self.mqtt.publish(b"/sensor/temp", bytes([temp]))
        self.mqtt.publish(b"/sensor/humidity", bytes([humidity]))

    def stall_for_messages(self, duration, interval):
        for _ in range((duration * 1000) // interval):
            self.mqtt.check_msg()
            time.sleep_ms(interval)

    def main_loop(self):
        while True:
            self.pulse(self.led_pwm, 50)
            self.publish_dht()
            self.stall_for_messages(30, 250)


meter = SolarMeter(MQTT_HOST, meter_pin=26, dht_pin=27, led_pin=13)
meter.main_loop()
