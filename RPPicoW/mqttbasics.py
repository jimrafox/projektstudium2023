"""
This is a general demo file for:
1) Reading dht20 sensor values and
2) sending sensor values via mqtt publish.
3) Subscribing to a mqtt topic and
4) switch a led on/of/blink on receiving corresponding message.
5) Measure respond time of the broker after publishing MQTT message.
"""

import time #for measuring response times
import binascii #for converting binary files and back
from dht20 import DHT20 #for reading sensor values
from umqtt.simple2 import MQTTClient 
from machine import I2C, Pin, Timer

# Create led object: 
led = Pin(16, Pin.OUT, value=0)

# Create Timer object:
tim = Timer()

# Define callback function timer:
def toggle_timer(t):
    led.toggle()

# Connect to wireless network:
def connect_wifi(ssid, password):
    import network
    # enable station interface and connect to WiFi access point
    nic = network.WLAN(network.STA_IF)
    nic.active(True)
    nic.connect(ssid, password) # should be changed to GGSEC:

    while not nic.isconnected():
        pass     
    print(nic.ifconfig())

# Creates a dht20 object with a I2C connection, returns temperature, humidity:
def read_dht20():
    i2c = I2C(0)
    dht20 = DHT20(i2c)
    values = {
        "tmp": dht20.dht20_temperature(),
        "hum": dht20.dht20_humidity()
        }
    return values

# MQTT connect:
def connect(server):
    # print('Connected to MQTT Broker "%s"' % (server))
    client = MQTTClient("myclient", server, 1883)
    client.connect()
    return client

# MQTT reconnect: 
def reconnect(server):
    # print('Failed to connect to MQTT broker, Reconnecting...' % (server))
    time.sleep(5)
    client.reconnect()

# MQTT subscribe to topic
def sub(client, topic, blocking_method=False):
    client.set_callback(callback_led)
    client.subscribe(topic)
    # print("Subscribed to {}".format(topic))

# MQTT publish via client
def pub(client, topic, message, qos):
    client.publish(topic, message, False, qos, False)

# MQTT publish, qos=1, callback for status, print response time broker:
def pub_status(client, topic, message):
    # print("publishing message: {}".format(message))
    start = time.ticks_ms()
    client.set_callback_status(callback_status)
    client.publish(topic, message, qos=1)
    client.wait_msg()
    delta = time.ticks_diff(time.ticks_ms(), start)
    print("respond time broker: %s ms" % delta)  

# Example callback function on received MQTT message:
def callback_led(topic, msg, retain, dup):
    print((topic, msg))
    if msg == b"on":
        led.value(1)
    elif msg == b"off":
        led.value(0)
    elif msg == b"toggle":
        led.toggle()
    elif msg == b"blinkon":
        tim.init(mode=Timer.PERIODIC, freq=10, callback=toggle_timer)
    elif msg == b"blinkoff":
        tim.deinit()

# callback function for broker response on publish
def callback_status(pid, status):
    print("Status:", end = " ") 
    if status== 1:
        print("successfully delivered")
    elif status == 0:
        print("timeout")
    elif status == 2:
        print("unknown PID")

'''
def pub_binary_file(client, filename, topic):
    f = open(filename, 'rb')
    fObj = f.read()
    msg = binascii.b2a_base64(fObj)
    # print('sending message %s on topic %s' % (msg, topic))
    pub_status(client, topic, msg)
    f.close()
'''
    
def pub_binary(client, topic, buffer, block_size=1024):
    '''
    MQTT publish a large buffer in seperate blocks.
    import: math, time, gc, micropython
    default block size 1024 bytes
    '''
    import math, time, gc
    import micropython as mp
    
    num_blocks = math.ceil(len(buffer)/block_size)
    print("Lenght of buffer in bytes: {}, block size: {}, number of blocks: {}".format(len(buffer), block_size, num_blocks))
    for i in range(num_blocks):
        try:
            gc.collect() 
            time.sleep_ms(100) 
            #print(">>> memory info <<<")
            #mp.mem_info()
            
            begin = i*block_size; end = begin+block_size;
            if end > len(buffer):
                end = len(buffer)
            print(">>> Time: {}, Sending block nr. {}. Begin: {}, end: {}".format(time.time(), str(i), begin, end))
            client.publish(topic, buffer[begin:end])
            print("ok")
            gc.collect() # ist das hier noch mal nötig? 
            #mp.mem_info() # 
            time.sleep_ms(1000) # testen ob das nötig ist
            if end == len(buffer):
                print("last block")
                client.publish(topic, "end")
                client.publish(topic, "Time: " + str(time.time()) +": All bytes sent.")
                
            else:
                print("block nr. {}".format(i))
                client.publish(topic, "Time: " + str(time.time()) +": Block "+ str(i+1)  + " of " + str(num_blocks)  + " sent.")
        except Exception as err:
            print("failed, error: {}".format(err))
            break

    
def main():
    server="192.168.178.36"
    topic = "proj/camera"
    ssid = 'GGSEC'
    password = 'uZQna3UipqvSYJhgkEcI'
    
    # Connect to wifi:
    connect_wifi(ssid, password)

    # Connect to MQTT broker:
    try:
        client = connect(server)
    except OSError as e:
        reconnect()

    # Subscribe to a topic:
    # sub(client, "proj/led", False)
    
    while True:
        # checking for messages in subscribed topics:
        # client.check_msg()
        
        # sending sensor data, no callback:
        msg1 = b'{'+str(read_dht20())+'}'
        print('sending message %s on topic %s' % (msg1, "proj/sensor"))
        pub(client, "proj/env", msg1, 0)
        
        time.sleep(1)
        
        
        # sending binary file via mqtt publish, with callback:
        f=open("file0.jpg", "rb")
        fObj=f.read()
        msg2 = binascii.b2a_base64(fObj)
        print('sending binary on topic {}'.format("proj/camera"))
        pub_binary(client, "proj/camera", msg2[:1000])
        f.close()
        
        input("press Enter")
        

if __name__ == '__main__':
   main()
