import uasyncio as asyncio
import M5
from M5 import *
from umqtt.simple import MQTTClient
import time
time.sleep(5)
import json
import network
from hardware import RFID  # Ensure correct import
import ubinascii
from machine import RTC, Pin  # Import RTC and Pin
import machine  # Ensure 'machine' is imported

import uos
import ntptime
import usocket
import socket

import os



# Global Variables
circle1 = None
image0 = None
B1 = None
B2 = None
B3 = None
pcs = None
circle0 = None
circle2 = None
circle3 = None
circle4 = None
circle5 = None  # Added circle5 for card scan status
error_label = None  # Added error_label for displaying errors
mqtt_client = None
wlan = None
wlan = network.WLAN(network.STA_IF)
rtc = None
rfid = None

B4 = None  #to display router num
B5 = None  #to display device number
number_part = None

#4 relays
relay_pin1 = None
relay_pin2 = None
relay_pin3 = None
relay_pin4 = None

Bundle_B1 = None
tch = None
device_id = None
optr_name = None
optn_name = None
Total = None
event_data = None
max_retries = 3
mqtt_connected = False  # Variable to track MQTT connection status
best_network = None
highest_dbm = -100
ota_update = None
c = None
restart_display = None
device_ip = None
device_name = None
log_mqtt = None


notification_msg = None #in case msg for notifiaction comes.

#MQTT_BROKER = '172.16.0.62'
#MQTT_BROKER = '192.168.3.22'
MQTT_BROKER = '206.189.135.233'
MQTT_PORT = 1883
MQTT_USER = 'edraak'                                              
MQTT_PASSWORD = 'edra@k112233'
#MQTT_USER = 'guest'
#MQTT_PASSWORD = 'guest'

#wlan = network.WLAN(network.STA_IF)


# OTA Server Configuration
OTA_SERVER = '192.168.3.22'
OTA_PORT = 80
OTA_PATH = "/main_ota_temp.py"
OTA_TOPIC = "output.rfid"

# MQTT Callback Function
def mqtt_callback(topic, msg):
    global Bundle_B1, tch, device_id, optr_name, optn_name, Total,relay_pin1,relay_pin2,relay_pin3,relay_pin4,ota_update,notification_msg
    try:
        optr = json.loads(msg)
        print(f'Message Received: {topic.decode()} {msg.decode()}')

        if "update" in optr and optr["update"] and "device_id" in optr and optr["device_id"] == device_id: 

        #if "update" in optr and optr["update"]: if you want to do OTA simulatenously for all devices at the same time, use this.
            Speaker.tone(1000, 50)
            B1.setVisible(False)
            B2.setVisible(False)
            B3.setVisible(False)
            B4.setVisible(False)
            pcs.setVisible(False)
            circle0.setVisible(False)
            circle1.setVisible(False)
            circle2.setVisible(False)
            circle3.setVisible(False)
            circle4.setVisible(False)
            circle5.setVisible(False) 
            Widgets.fillScreen(0xFFFF00)  # Set initial background color  
            ota_update=Widgets.Label("OTA_UPDATE", 18, 90, 1.5, 0xff0000, 0xFFFF00, Widgets.FONTS.DejaVu18)
            ota_update.setVisible(True)
            time.sleep(10)

            perform_ota()

        elif "status" in optr and optr["status"] == "error" and "device_id" in optr and optr["device_id"] == device_id:
            notification_msg = optr['message']
            display_msg(notification_msg)
     

        elif optr['device_id'] == device_id:
            print('Device ID Match')

            Speaker.tone(1000, 50)
            optr_name = optr['Operator']
            optn_name = optr['Operation']
            Bundle_B1 = optr['Bundle']
            Total = optr['total_bundle']
            tch = optr['Color']
            
            print(f'color: {tch}')

            time.sleep_ms(30)

            # Control relay pins based on `tch` color
            if tch == 'red':  # Red
                print('Red')
                relay_pin1.value(1)  # Activate relay 1
                relay_pin2.value(1)
                relay_pin3.value(0)
                relay_pin4.value(1)
                print('Red color detected, relay 1 activated.')
              
            elif tch == 'yellow':  # yellow
                relay_pin1.value(1)
                relay_pin2.value(1)  # Activate relay 2
                relay_pin3.value(1)
                relay_pin4.value(0)
                print("Orange color detected, relay 2 activated.")
            elif tch == 'green':  # Green
                relay_pin1.value(1)
                relay_pin2.value(0)
                relay_pin3.value(1)  # Activate relay 3
                relay_pin4.value(1)
                print("Green color detected, relay 3 activated.")
            elif tch == 'blue':  # Blue
                relay_pin1.value(0)
                relay_pin2.value(1)
                relay_pin3.value(1)
                relay_pin4.value(1)  # Activate relay 4
                print("Blue color detected, relay 4 activated.")
            else:
                # If the color code doesn't match any predefined color, turn all relays off
                relay_pin1.value(1)
                relay_pin2.value(1)
                relay_pin3.value(1)
                relay_pin4.value(1)
                print("No matching color code, all relays turned off.")




            # Update UI components
            B1.setText(str(optr_name))
            B2.setText(str(optn_name))
            pcs.setText(f"{Bundle_B1}/{Total}")
            B3.setText(f"Bundle Pieces: {Bundle_B1}")

            # Set colors
            B1.setColor(0xffffff, tch)
            B2.setColor(0xffffff, tch)
            B3.setColor(0xffffff, tch)
            pcs.setColor(0xffffff, tch)
            circle3.setColor(color=0xffffff, fill_c=tch if optr.get('Optr_flag') == 0 else 0xffffff)
            circle2.setColor(color=0xffffff, fill_c=tch if optr.get('Optn_flag') == 0 else 0xffffff)
            circle4.setColor(color=0xffffff, fill_c=tch if optr.get('Bndl_flag') == 0 else 0xffffff)

            print('UI Updated')
        
    except Exception as e:
        print(f"Error processing MQTT message: {e}")

# Wi-Fi Connection Function
async def connect_wifi():
    global B4,device_ip,retries,best_network
    print(f"Device IP received from flash is {device_ip}")
    max_retries = 3
    highest_dbm = -100
    # List of known SSID and password pairs
    known_networks = [
      ("Edraak-2", "edraak123"),
      #("Edraak-3", "edraak123"),
      #("Edraak-4", "edraak123")
      ]
    blinking=asyncio.create_task(blink_circle())

    # Set up Wi-Fi connection
    
    wlan.active(True)
    await asyncio.sleep(1)
    #wlan.ifconfig((device_ip, '255.255.248.0', '172.16.48.240', '172.16.0.1'))  # Static IP configuration
    

    # Iterate over known networks
    for ssid, password in known_networks:
       print(f"Attempting to connect to {ssid}...")
       #wlan.active(True)  # Ensure Wi-Fi is active
       #time.sleep(1)
       wlan.disconnect()  # Disconnect any active connection
       #time.sleep(2)
       await asyncio.sleep(2)
       retries = 0
       #wlan.active(True)
       #time.sleep(60)
       wlan.connect(ssid, password)  # Start connection attempt
       #time.sleep(5)
       await asyncio.sleep(5)
       print(f"Connection status before while loop: {wlan.isconnected()}")
       if wlan.isconnected():
         signal_strength = wlan.status('rssi')
         print(f"Wi-Fi Signal Strength: {signal_strength} dBm")
         if signal_strength > highest_dbm:
             highest_dbm = signal_strength
             best_network = ssid

       while not wlan.isconnected() and retries < max_retries:
         try:
            print(f'Attempt {retries + 1}: Connecting to Wi-Fi...')
            wlan.connect(ssid, password)  # Start connection attempt
            #time.sleep(1)
            await asyncio.sleep(1)
            if wlan.isconnected():  
                print(f"Connected to network with IP Address: {wlan.ifconfig()[0]}")
                
                signal_strength = wlan.status('rssi')
                print(f"Wi-Fi Signal Strength: {signal_strength} dBm")
                if signal_strength > highest_dbm:
                  highest_dbm = signal_strength
                  best_network = ssid
                
                break  # Exit the while loop
            retries += 1
         except Exception as e:
            print(f"Unable to connect to {ssid}: {e}")
            retries += 1
    #Best Network scan completed   
    wlan.disconnect()  # Disconnect any active connection
    #time.sleep_ms(2)
    await asyncio.sleep(.002)
    #wlan.ifconfig((device_ip, '255.255.248.0', '172.16.48.240', '172.16.0.1'))  # Static IP configuration
    print(f"Best network found is:  {best_network} (Strength: {highest_dbm}dbm")
    wlan.connect(best_network, 'edraak123')  # Start connection attempt
    #time.sleep(5)
    await asyncio.sleep(5)
    retries = 0
    
    while not wlan.isconnected() and retries < max_retries:
        try:
            print(f'Attempt {retries + 1}: Connecting to Wi-Fi...')
            wlan.connect(best_network, 'edraak123')  # Update with your Wi-Fi SSID and password
            #wlan.connect('Yasir (LDN Net 0321-4628595)', 'ymabmu5570')
            await asyncio.sleep(5)  # Wait for 5 seconds before checking again
            if wlan.isconnected():
                break
            retries += 1
        except Exception as e:
            print(f'Wi-Fi connection error: {e}')
            retries += 1
            await asyncio.sleep(5)
    
    # Stop blinking
    blinking.cancel()
    

    if wlan.isconnected():
        ip_address = wlan.ifconfig()[0]
        ssid = wlan.config('essid')
        if ip_address != '0.0.0.0':
            print('Wi-Fi Connected')
            print(f'IP Address: {ip_address}')
            print(f"Connected to Wi-Fi: {ssid}")
            circle0.setColor(color=0xffffff, fill_c=0x00ff00)  # Green color for Wi-Fi connected
            if ssid == 'Edraak-2':
               B4 = Widgets.Label("2", 84, 8, 1.0, 0x00ff00, 0x000000, Widgets.FONTS.DejaVu18)
               B4.setVisible(True)
            elif ssid == 'Edraak-3':
               B4 = Widgets.Label("2", 84, 8, 1.0, 0x00ff00, 0x000000, Widgets.FONTS.DejaVu18)
               B4.setVisible(True)
            elif ssid == 'Edraak-4':
               B4 = Widgets.Label("4", 84, 8, 1.0, 0x00ff00, 0x000000, Widgets.FONTS.DejaVu18)
               B4.setVisible(True)
            else:
               B4 = Widgets.Label("U", 84, 8, 1.0, 0x00ff00, 0x000000, Widgets.FONTS.DejaVu18)
               B4.setVisible(True)
        else:
            print('Connected but no valid IP address obtained')
    else:
        print('Failed to connect to Wi-Fi after retries')
        circle0.setColor(color=0xffffff, fill_c=0xFF0000)  # Red color for Wi-Fi disconnected
        # Consider handling this case, possibly restarting the device
   

 

# MQTT Connection Function
async def connect_mqtt():
    global mqtt_client, device_id, mqtt_connected,device_name
    #wlan.active(True)
    print(f"Device ID received from flash is {device_name}")
    while True:
        try:
            mqtt_client = MQTTClient(device_name, MQTT_BROKER, port=MQTT_PORT, user=MQTT_USER, password=MQTT_PASSWORD, keepalive=60)
            mqtt_client.set_callback(mqtt_callback)
            mqtt_client.connect()
            await asyncio.sleep(1)
            print('MQTT Connected')
            mqtt_client.subscribe('output/rfid')
            time.sleep(2) 
            device_id = ubinascii.hexlify(wlan.config('mac')).decode('utf-8')            
            print(f'Device ID: {device_id}')
            mqtt_client.publish('input.rfid', json.dumps({'IP': wlan.ifconfig()[0], 'MacID': device_id}))
            circle1.setColor(color=0xffffff, fill_c=0x00FF00)  # Green color for MQTT connected
            mqtt_connected = True  # Update connection status
            break  # Exit the loop once connected
        except Exception as e:
            print(f'Failed to connect to MQTT broker: {e}')
            circle1.setColor(color=0xffffff, fill_c=0xFF0000)  # Red color for MQTT disconnected
            mqtt_connected = False  # Update connection status
            await asyncio.sleep(5)  # Wait before retrying


# Keep-Alive and Reconnection Task
async def mqtt_heartbeat():
    global mqtt_client, mqtt_connected
    while True:
        try:
            if mqtt_client:
                mqtt_client.ping()
        except OSError:
            print('MQTT disconnected, attempting to reconnect...')
            mqtt_connected = False
            circle1.setColor(color=0xffffff, fill_c=0xFF0000)  # Red color for MQTT disconnected
            await connect_mqtt()
        await asyncio.sleep(10)  # Ping every 10 seconds

# MQTT Message Checking Task
async def mqtt_check_messages():
    global mqtt_client
    while True:
        try:
            if mqtt_client:
                mqtt_client.check_msg()
        except OSError as e:
            print(f'MQTT Error: {e}')
            await connect_mqtt()
        await asyncio.sleep(0.1)  # Check for messages every 100ms

def perform_ota():
    global c,restart_display,log_mqtt
    log_error('OTA Update')
                              
    

    gc.collect()  # Run garbage collection to free up memory
    free_memory = gc.mem_free()
    print(f"Free memory before OTA: {free_memory} bytes")
    time.sleep_ms(10)  # Small delay to allow system to stabilize

    print("Checking for OTA update...")
    ota_file = OTA_PATH
    try:
        # Create a socket and connect to the OTA server
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((OTA_SERVER, OTA_PORT))
        print('Connected to OTA server')

        # Send an HTTP GET request
        request = f"GET {ota_file} HTTP/1.1\r\nHost: {OTA_SERVER}\r\nConnection: close\r\n\r\n"
        s.send(request.encode())
        print("Request sent")

        # Open the file to write OTA data directly
        with open('/flash/main_ota_temp.py', 'wb') as f:
            headers_received = False
            leftover_data = b""
            
            while True:
                data = s.recv(1024)  # Receive in smaller chunks
                if not data:
                    break
                
                # Combine with any leftover data from previous chunks
                data = leftover_data + data
                
                if not headers_received:
                    # Look for the end of headers
                    header_end = data.find(b"\r\n\r\n")
                    if header_end != -1:
                        headers_received = True
                        # Remove headers from the data
                        data = data[header_end + 4:]
                    else:
                        # Headers not yet fully received; store data for the next chunk
                        leftover_data = data
                        continue
                
                # Write chunk to file if it's after headers
                if headers_received and data:
                    f.write(data)
                    gc.collect()  # Run garbage collection to free memory
                    time.sleep_ms(10)

        # Close the socket
        s.close()

        #print("OTA update successful. Restarting in 5 seconds...")
        for i in range(5, 0, -1):  # Start at 5, go down to 1
           print(f"Restarting in {i} seconds...")
           time.sleep(1)
           restart_display=Widgets.Label(f"{i}sec", 100, 180, 1, 0x000000, 0xFFFF00, Widgets.FONTS.DejaVu18)
           restart_display.setVisible(True)
        #time.sleep(5)  # Wait before restarting
        machine.reset()  # Restart to apply the new firmware

    except Exception as e:
        print(f"Failed to download OTA file: {e}")
    finally:
        if 's' in locals():
            s.close()

def get_ip_details(filename):
    global device_ip, device_name,B5,number_part,x
    try:
        # Open the file in read mode
        with open(filename, 'r') as file:
            lines = file.readlines()  # Read all lines into a list
            if len(lines) >= 2:  # Ensure the file has at least two lines
                # Strip whitespace and convert to integers
                device_ip = (lines[0].strip())
                device_name = (lines[1].strip())
                
            else:
                print("File does not contain enough data.")
                return None
        number_part = int(device_name.split('_')[1][1:])  # Extract the number part
        x = str(number_part)
        print(f"{number_part}")
        B5 = Widgets.Label(x, 108, 197, 1.0, 0x00ff00, 0x000000, Widgets.FONTS.DejaVu18)
        B5.setVisible(True)
    except Exception as e:
        print(f"Error reading file: {e}")
        return None

#this task runs parallel with connect_wifi(). it just blinks the wifi circle while connection is establishing
async def blink_circle(): 
    global circle0
    while True:
        circle0.setColor(color=0xffffff, fill_c=0xFFFF00)  # Yellow color
        await asyncio.sleep(0.5)  # Half a second on
        circle0.setColor(color=0xffffff, fill_c=0x000000)  # Off
        await asyncio.sleep(0.5)  # Half a second off


def log_error(error_message):
    global log_mqtt,best_network,device_name
    try:
        
        # Open the file in append mode so it doesn't overwrite previous content
        #with open('/flash/error_log.txt', 'a') as file:
        timestamp = "{:04}-{:02}-{:02} {:02}:{:02}:{:02}".format(*time.localtime()[:6])
        log_mqtt = json.dumps({'device_id': device_id,'device name': device_name, 'Router': best_network, 'message': error_message,'Time' : timestamp})
        mqtt_client.publish('input.rfid', log_mqtt)
          
        print("Error logged successfully.")
    except Exception as e:
        print("Failed to log error:", e)


def display_msg(notification_display):
  global show1,show2, words,first_word,second_word
  Speaker.tone(1000, 50)
  B1.setVisible(False)
  B2.setVisible(False)
  B3.setVisible(False)
  B4.setVisible(False)
  pcs.setVisible(False)
  circle0.setVisible(False)
  circle1.setVisible(False)
  circle2.setVisible(False)
  circle3.setVisible(False)
  circle4.setVisible(False)
  circle5.setVisible(False) 
  Widgets.fillScreen(0xFFFF00)  # Set initial background color  
  
  words = notification_display.split()
  if len(words) == 2:  # Ensure there are exactly two words
        first_word, second_word = words
        show1=Widgets.Label(first_word, 50, 90, 1.5, 0xff0000, 0xFFFF00, Widgets.FONTS.DejaVu18)
        show2=Widgets.Label(second_word, 50, 140, 1.5, 0xff0000, 0xFFFF00, Widgets.FONTS.DejaVu18)
        show1.setVisible(True)
        show2.setVisible(True)
  else:
        first_word, second_word = notification_display, None 
        show1=Widgets.Label(first_word, 50, 90, 1.5, 0xff0000, 0xFFFF00, Widgets.FONTS.DejaVu18)
        show1.setVisible(True)
  time.sleep(5)
  #back to normal
  Widgets.fillScreen(0x000000)
  B1.setVisible(True)
  B2.setVisible(True)
  B3.setVisible(True)
  B4.setVisible(True)
  pcs.setVisible(True)
  circle0.setVisible(True)
  circle1.setVisible(True)
  circle2.setVisible(True)
  circle3.setVisible(True)
  circle4.setVisible(True)
  circle5.setVisible(True) 
  return


# Main Loop Task
async def main_loop():
    global mqtt_client, wlan, rfid, device_id, event_data, mqtt_connected, circle5, error_label,log_mqtt,device_name
    scan_count = 0
    iteration_count = 0
    prev_card_present = False  # To track state changes
    error_count = 0
    max_tries = 3  # Maximum number of allowed errors before restarting

    while True:
        try:
            iteration_count += 1
            rfid=RFID()
            time.sleep_ms(10)
            error_count = 0

            if rfid:
                try:
                    # Attempt to detect a card
                    card_present = rfid.is_new_card_present()

                    # Print status only when it changes
                    if card_present != prev_card_present:
                        if card_present:
                            print("New RFID card detected")
                        else:
                            print("No RFID card detected")
                        prev_card_present = card_present

                    if card_present:
                        # Read card UID
                        card_uid = rfid.read_card_uid()
                        #event_data = ''.join(['%02X' % x for x in card_uid])
                        #event_data = ubinascii.hexlify(str(card_uid).encode()).decode('utf-8')
                        #event_data = int.from_bytes(card_uid, 'little')
                        event_data = f'{int.from_bytes(card_uid, "little"):010d}' #use this if 0 is to be read

                        print(event_data)  # This will print the UID as a string with leading zeros
                        


                        print(f"Card UID: {event_data}")
                        scan_count += 1
                        print(f"Total scans: {scan_count}")
                        if len(str(event_data)) > 5:
                          # Turn the indicator green
                          circle5.setColor(color=0xffffff, fill_c=0x00FF00)  # Green color
                          # Clear error message if any
                          error_label.setText("")
                          error_label.setVisible(False)
                          # Wait for a short time
                          await asyncio.sleep(0.5)
                          # Return the indicator to default color
                          circle5.setColor(color=0xffffff, fill_c=0xffffff)  # Default color
                          Speaker.tone(2000, 50)
                          if mqtt_connected:
                              message = json.dumps({'device_id': device_id, 'card_uid': event_data})
                              print(f"Publishing message: {message}")
                              try:
                                  mqtt_client.publish('input.rfid', message)
                                  print("Message published to MQTT")
                              except Exception as e:
                                  print(f"Error publishing to MQTT: {e}")
                                  mqtt_connected = False
                          else:
                              print('MQTT Client not connected')
                        else:
                          Speaker.tone(1500, 100)
                          circle5.setColor(color=0xffffff, fill_c=0xFFFF00)  # set the color to yellow
                        await asyncio.sleep(0.5)  # Wait before next read
                        if len(str(event_data)) < 5:
                          circle5.setColor(color=0xffffff, fill_c=0xffffff)
                        else:
                          pass                         
                    else:
                        # No card present
                        pass  # Do nothing
                except Exception as e:
                    print(f"Exception during RFID operation: {e}")
                    log_error(f"Exception during RFID operation: {e}")

                    import sys
                    sys.print_exception(e)
                    error_count += 1
                    # Display error on the device screen
                    error_message = f"Error: {e}"
                    error_label.setText(error_message)
                    error_label.setVisible(True)
                    # Change the indicator to red
                    circle5.setColor(color=0xffffff, fill_c=0xFF0000)  # Red color for error
                    # Attempt to reset the RFID module
                    try:
                        rfid = RFID()
                        time.sleep(7)
                        print("RFID reinitialized after exception")
                        log_error("RFID reinitialized after exception")
                        error_count = 0  # Reset error count after successful reinitialization
                        # Clear error message
                        error_label.setText("")
                        error_label.setVisible(False)
                        # Return the indicator to default color
                        circle5.setColor(color=0xffffff, fill_c=0xffffff)
                    except Exception as e:
                        print(f"Error reinitializing RFID: {e}")
                        log_error(f"Error reinitializing RFID: {e}")
                        rfid = None
                    # If error count exceeds max_tries, restart the device
                    if error_count >= max_tries:
                        print(f"Maximum error count reached ({error_count}). Restarting device.")
                        log_error(f"Maximum error count reached ({error_count}). Restarting device.")
                        error_label.setText("Restarting device due to errors...")
                        error_label.setVisible(True)
                        # Restart the device
                        import machine
                        machine.reset()
            else:
                print("RFID object is None, attempting to reinitialize")
                

            # Manage memory less frequently
            if iteration_count % 50 == 0:
                import gc
                gc.collect()
                free_memory = gc.mem_free()
                print(f"Free memory: {free_memory}")

        except Exception as e:
            print(f"Exception in main_loop: {e}")
            log_error(f"Exception in main_loop: {e}")
            import sys
            sys.print_exception(e)
            error_count += 1
            # Display error message
            error_message = f"Error: {e}"
            error_label.setText(error_message)
            error_label.setVisible(True)
            # If error count exceeds max_tries, restart the device
            if error_count >= max_tries:
                print(f"Maximum error count reached ({error_count}). Restarting device.")
                log_error(f"Maximum error count reached ({error_message}). Restarting device.")
                error_label.setText("Restarting device due to errors...")
                error_label.setVisible(True)
                import machine
                machine.reset()
        await asyncio.sleep(0.1)

# Initialization Function
async def setup():
    global circle1, image0, B1, B2, B3, pcs, circle0, circle2, circle3, circle4, circle5, error_label, rtc, rfid,relay_pin1,relay_pin2,relay_pin3,relay_pin4

    M5.begin()
    

    relay_pin1 = machine.Pin(13, machine.Pin.OUT)  # Port A Pin 13
    relay_pin2 = machine.Pin(2, machine.Pin.OUT)  # Port A Pin 15
    relay_pin3 = machine.Pin(1, machine.Pin.OUT)   # Port B Pin 1
    relay_pin4 = machine.Pin(15, machine.Pin.OUT)   # Port B Pin 2

    #by default all pins are high, which means 0v at outpins and all 4 lights will be OFF

    #relay_pin1.value(1)
    #relay_pin2.value(1)
    #relay_pin3.value(1)
    #relay_pin4.value(1)




    circle1 = Widgets.Circle(130, 12, 7, 0xffffff, 0xffffff)  # MQTT status indicator
    image0 = Widgets.Image("res/img/asset (Custom).png", 0, 0)
    
    B1 = Widgets.Label("Operator", 77, 33, 1.0, 0xffffff, 0x000000, Widgets.FONTS.DejaVu18)
    B2 = Widgets.Label("Operation", 72, 57, 1.0, 0xffffff, 0x000000, Widgets.FONTS.DejaVu18)
    B3 = Widgets.Label("Bundle Pieces : 0", 39, 81, 1.0, 0xffffff, 0x000000, Widgets.FONTS.DejaVu18)
    pcs = Widgets.Label("00/00", 38, 122, 1.0, 0xffffff, 0x000000, Widgets.FONTS.DejaVu40)
    circle0 = Widgets.Circle(110, 12, 7, 0xffffff, 0xffffff)  # Wi-Fi status indicator
    circle2 = Widgets.Circle(122, 223, 7, 0xffffff, 0xffffff)
    circle3 = Widgets.Circle(97, 223, 7, 0xffffff, 0xffffff)
    circle4 = Widgets.Circle(147, 223, 7, 0xffffff, 0xffffff)
    circle5 = Widgets.Circle(150, 12, 7, 0xffffff, 0xffffff)  # Card scan status indicator
    error_label = Widgets.Label("", 10, 180, 1.0, 0xffffff, 0xff0000, Widgets.FONTS.DejaVu18)
    error_label.setVisible(False)

    image0.setVisible(True)
    Speaker.tone(1500, 100)
    await asyncio.sleep(1)
    rtc = RTC()  # RTC is now properly imported
    #ntptime.settime()
    try:
        rfid = RFID()
        print(f"RFID object initialized: {rfid}")
    except Exception as e:
        print(f"Error initializing RFID: {e}")
        rfid = None
    print('Hardware initialized')

    Widgets.fillScreen(0x000000)  # Set initial background color
    Speaker.setVolumePercentage(1)
    image0.setVisible(False)
    # Make UI elements visible
    B1.setVisible(True)
    B2.setVisible(True)
    B3.setVisible(True)
    pcs.setVisible(True)
    circle0.setVisible(True)
    circle1.setVisible(True)
    circle2.setVisible(True)
    circle3.setVisible(True)
    circle4.setVisible(True)
    circle5.setVisible(True)  # Make the new indicator visible
    error_label.setVisible(False)  # Initially not visible
    print('UI Initialized')
    get_ip_details("ip.txt")

    await connect_wifi()
    time.sleep(2)
    await connect_mqtt()
    

# Main Function
async def main():
    await setup()
    # Start concurrent tasks
    asyncio.create_task(mqtt_heartbeat())
    asyncio.create_task(mqtt_check_messages())
    
    await main_loop()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Exception: {e}")
        import sys
        sys.print_exception(e)
        # Handle exceptions, possibly restart the device
