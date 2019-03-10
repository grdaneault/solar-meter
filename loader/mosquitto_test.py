import sys
import time

import paho.mqtt.client as mqtt

if sys.argv[1] == 'sub':
    # The callback for when the client receives a CONNACK response from the server.
    def on_connect(client, userdata, flags, rc):
        print("Connected with result code " + str(rc))

        # Subscribing in on_connect() means that if we lose the connection and
        # reconnect then subscriptions will be renewed.
        # client.subscribe("$SYS/#")
        client.subscribe("/solar/eim/wattHours")
        client.subscribe("/sensor/temp")
        client.subscribe("/sensor/humidity")


    # The callback for when a PUBLISH message is received from the server.
    def on_message(client, userdata, msg):
        print(msg.topic + " " + str(msg.payload))


    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect("192.168.1.215", 1883, 60)

    # Blocking call that processes network traffic, dispatches callbacks and
    # handles reconnecting.
    # Other loop*() functions are available that give a threaded interface and a
    # manual interface.
    client.loop_forever()

elif sys.argv[1] == 'pub':
    client = mqtt.Client()
    client.connect("192.168.1.215", 1883, 60)

    client.loop_start()

    i = 0
    while True:
        i += 1
        client.publish("/solar/eim/wattHours", float(input("Enter value: ")))
