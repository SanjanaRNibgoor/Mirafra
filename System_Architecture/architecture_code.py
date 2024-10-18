"# Sample system architecture code" 
#Python Modules
import argparse
import array
import random
import sys
import time
import threading
import subprocess

from datetime import datetime
from random import randint

#D-bus Api's
import dbus
import dbus.mainloop.glib
from gi.repository import GLib
import bluezutils
import dbus.exceptions
import dbus.service

try:
  from gi.repository import GObject
except ImportError:
  import gobject as GObject

import requests
import json

# Global variables for the main loop and application instance
mainloop = None
app = None
service_manager = None  # To be defined later
test_advertisement = None


BLUEZ_SERVICE_NAME = 'org.bluez'
GATT_MANAGER_IFACE = 'org.bluez.GattManager1'
DBUS_OM_IFACE =      'org.freedesktop.DBus.ObjectManager'
DBUS_PROP_IFACE =    'org.freedesktop.DBus.Properties'

GATT_SERVICE_IFACE = 'org.bluez.GattService1'
GATT_CHRC_IFACE =    'org.bluez.GattCharacteristic1'
GATT_DESC_IFACE =    'org.bluez.GattDescriptor1'

LE_ADVERTISING_MANAGER_IFACE = 'org.bluez.LEAdvertisingManager1'


LE_ADVERTISEMENT_IFACE = 'org.bluez.LEAdvertisement1'

class InvalidArgsException(dbus.exceptions.DBusException):
    _dbus_error_name = 'org.freedesktop.DBus.Error.InvalidArgs'

class NotSupportedException(dbus.exceptions.DBusException):
    _dbus_error_name = 'org.bluez.Error.NotSupported'

class NotPermittedException(dbus.exceptions.DBusException):
    _dbus_error_name = 'org.bluez.Error.NotPermitted'

class InvalidValueLengthException(dbus.exceptions.DBusException):
    _dbus_error_name = 'org.bluez.Error.InvalidValueLength'

class FailedException(dbus.exceptions.DBusException):
    _dbus_error_name = 'org.bluez.Error.Failed'

#Raspi PIN
import RPi.GPIO as GPIO  # Assuming you're using a Raspberry Pi for GPIO control
from gi.repository import GObject

# Define the GPIO pin numbers for the door lock and LED
DOOR_LOCK_PIN = 18  # Set the pin number for door lock control

# Setup GPIO pins
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(DOOR_LOCK_PIN, GPIO.OUT)

# Initialize the GPIO
def setup_gpio():
    GPIO.setmode(GPIO.BCM)  # Use Broadcom pin numbering
    GPIO.setup(DOOR_LOCK_PIN, GPIO.OUT)  # Set DOOR_LOCK_PIN as output
    GPIO.output(DOOR_LOCK_PIN, GPIO.LOW)  # Ensure door is locked initially (LED OFF)

def cleanup_gpio():
    GPIO.cleanup()    
setup_gpio()  # Initialize GPIO at the start of the program
global auto_lock_duration
auto_lock_duration = 10 


#===========================================================================================================
#         ThingSpeak channel details
#===========================================================================================================
# Replace with your ThingSpeak channel details
API_KEY = "ABWVZO1JHQB5YFZ1"
CHANNEL_ID = "2661025"

READ_URL = f"https://api.thingspeak.com/channels/{CHANNEL_ID}/feeds.json?api_key={API_KEY}&results=1"

THINGSPEAK_CHANNEL_ID = '2661025'  # Your channel ID
THINGSPEAK_UPDATE_URL = 'https://api.thingspeak.com/update'
THINGSPEAK_READ_API_KEY = 'ABWVZO1JHQB5YFZ1'  # Use your READ API Key here
THINGSPEAK_WRITE_API_KEY = 'BDRPE0TZUXUQTF5N'

def get_password_from_thingspeak():
    url = f"https://api.thingspeak.com/channels/{CHANNEL_ID}/status.json"
    params = {
        "api_key": API_KEY,
        #"results": 1  # Get only the most recent entry
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()      
        data = response.json()
       
        # Extract the most recent entry
        feeds = data.get('feeds', [])
        if feeds:
            most_recent_feed = feeds[-1]  # Get the last (most recent) entry
           # print(f"Most recent feed: {most_recent_feed}")  # Print the entire feed for debugging
            status = most_recent_feed.get('status', 'No status field available')
            # Print all fields for debugging
            for key, value in most_recent_feed.items():
                print(f"{key}: {value}")
            return status
        else:
            print("No feed data available.")
            return None
    except requests.RequestException as e:
        print(f"An error occurred while fetching data: {e}")
        return None

# Update ThingSpeak with a new password
# Update the cloud password
def update_cloud_password(new_password):
    try:
        response = requests.post(THINGSPEAK_UPDATE_URL, {
            'api_key': THINGSPEAK_WRITE_API_KEY,  # Your WRITE API Key here
            'status': new_password  # Update the 'status' field with the new password
        })
        if response.status_code == 200:
            print(f"Updated cloud password to: {new_password}")
        else:
            print("Error updating cloud password.")
    except Exception as e:
        print(f"Exception occurred while updating cloud password: {e}")

# Generate a unique password (for example, a random 4-digit number)
def generate_unique_password():
    return str(random.randint(1000, 9999)) 


#===========================================================================================================
#        New Paired Devices Feature
#===========================================================================================================

class BluetoothManager_pair:
    def __init__(self):
        # Set up the D-Bus main loop
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        self.bus = dbus.SystemBus()
        self.managed_objects = {}
        self.listener_running = True

        # Start bluetoothctl in a separate thread
        self.btctl_process = subprocess.Popen(
            ['bluetoothctl'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        self.listener_thread = threading.Thread(target=self.listen_to_bluetoothctl)
        self.listener_thread.start()

        # Discover devices
        self.adapter_path = self.get_adapters()
        if self.adapter_path:
            self.start_discovery()
        else:
            print("No Bluetooth adapter found.")
            sys.exit(1)

    def get_adapters(self):
        """Get available Bluetooth adapters."""
        obj_manager = dbus.Interface(self.bus.get_object("org.bluez", "/"), "org.freedesktop.DBus.ObjectManager")
        managed_objects = obj_manager.GetManagedObjects()
        
        for path, interfaces in managed_objects.items():
            if "org.bluez.Adapter1" in interfaces:
                return path  # Return the first found adapter path
        return None

    def start_discovery(self):
        """Start scanning for Bluetooth devices."""
        adapter = dbus.Interface(self.bus.get_object("org.bluez", self.adapter_path), "org.bluez.Adapter1")
        try:
            adapter.StartDiscovery()
            print("Starting discovery...")
            time.sleep(10)  # Allow some time for discovery
            self.stop_discovery()
        except dbus.DBusException as e:
            print(f"Failed to start discovery: {e}")
            sys.exit(1)

    def stop_discovery(self):
        """Stop scanning for Bluetooth devices."""
        adapter = dbus.Interface(self.bus.get_object("org.bluez", self.adapter_path), "org.bluez.Adapter1")
        try:
            adapter.StopDiscovery()
            print("Stopped discovery.")
        except dbus.DBusException as e:
            print(f"Failed to stop discovery: {e}")

    def refresh_managed_objects(self):
        """Refresh the list of managed D-Bus objects."""
        obj_manager = dbus.Interface(self.bus.get_object("org.bluez", "/"), "org.freedesktop.DBus.ObjectManager")
        self.managed_objects = obj_manager.GetManagedObjects()

    def list_devices(self):
        """List discovered Bluetooth devices."""
        self.refresh_managed_objects()
        devices = []
        for path, interfaces in self.managed_objects.items():
            if "org.bluez.Device1" in interfaces:
                device_props = interfaces["org.bluez.Device1"]
                device_address = device_props.get("Address", "Unknown")
                paired = device_props.get("Paired", False)
                connected = device_props.get("Connected", False)
                devices.append((device_address, path, paired, connected))
        return devices

    def get_device(self, device_address):
        """Retrieve a device object by its address."""
        device_path = f"/org/bluez/hci0/dev_{device_address.replace(':', '_')}"
        if device_path in self.managed_objects:
            return dbus.Interface(self.bus.get_object("org.bluez", device_path), "org.bluez.Device1")
        else:
            print(f"Device {device_address} not found in managed objects.")
            return None

    def pair_device(self, device_address):
        """Pair with a new device using the specified address."""
        device = self.get_device(device_address)
        if not device:
            return

        properties = dbus.Interface(device, "org.freedesktop.DBus.Properties")
        try:
            paired = properties.Get("org.bluez.Device1", "Paired")
            if paired:
                print(f"Device {device_address} is already paired.")
                return
        except dbus.DBusException as e:
            print(f"Failed to check pairing status: {e}")
            return

       # confirmation = input(f"Do you want to pair with {device_address}? (yes/no): ").strip().lower()
        confirmation = 'yes'
        if confirmation != 'yes':
            print("Pairing cancelled.")
            return

        try:
            device.Pair()
            print(f"Pairing with {device_address}...")
            time.sleep(10)  # Wait longer to allow pairing to process
            self.check_pairing_status(device_address)
        except dbus.DBusException as e:
            print(f"Failed to initiate pairing: {e}")

    def check_pairing_status(self, device_address):
        """Check if the device is paired successfully."""
        device = self.get_device(device_address)
        if not device:
            return

        properties = dbus.Interface(device, "org.freedesktop.DBus.Properties")
        try:
            paired = properties.Get("org.bluez.Device1", "Paired")
            if paired:
                print(f"Successfully paired with {device_address}.")
                exit_confirmation = input("Do you want to exit the Bluetooth manager? (yes/no): ").strip().lower()
                if exit_confirmation == 'yes':
                    self.close()
            else:
                print(f"Failed to pair with {device_address}.")
        except dbus.DBusException as e:
            print(f"Failed to check pairing status: {e}")

    def close(self):
        """Close the bluetoothctl process and clean up."""
        self.listener_running = False  # Signal the listener thread to stop
        self.btctl_process.stdin.write('exit\n')
        self.btctl_process.stdin.flush()
        self.btctl_process.terminate()
        self.listener_thread.join()  # Wait for the listener thread to finish
        print("Bluetooth manager closed.")

    def listen_to_bluetoothctl(self):
        """Listen to bluetoothctl output for pairing requests."""
        while self.listener_running:
            output = self.btctl_process.stdout.readline()
            if "Confirm passkey" in output:
                print(output.strip())
                #user_response = input("Do you want to accept this pairing request? (yes/no): ").strip().lower()
                user_response = 'yes'
                if user_response == 'yes':
                    self.btctl_process.stdin.write('yes\n')
                    self.btctl_process.stdin.flush()
                else:
                    self.btctl_process.stdin.write('no\n')
                    self.btctl_process.stdin.flush()
            elif output == '' and self.btctl_process.poll() is not None:
                break

#===========================================================================================================
#         Paired Devices Automatic Unlock Feature
#===========================================================================================================
import dbus
import dbus.mainloop.glib
import threading

class BluetoothManager:
    def __init__(self, auto_lock_duration):
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        self.bus = dbus.SystemBus()

        # Initialize GPIO
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(DOOR_LOCK_PIN, GPIO.OUT)

        self.door_locked = True
        self.monitoring_paused = False
        self.auto_lock_timer = None
        self.auto_lock_duration = auto_lock_duration
        self.connected_devices = set()
        self.refresh_managed_objects()

    def refresh_managed_objects(self):
        obj_manager = dbus.Interface(self.bus.get_object("org.bluez", "/"), "org.freedesktop.DBus.ObjectManager")
        self.managed_objects = obj_manager.GetManagedObjects()

    def list_paired_devices(self):
        paired_devices = []
        for path, interfaces in self.managed_objects.items():
            if "org.bluez.Device1" in interfaces:
                device_props = interfaces["org.bluez.Device1"]
                if device_props.get("Paired", False):
                    device_address = device_props["Address"]
                    paired_devices.append((device_address, path))
        return paired_devices

    def device_status(self, device_path):
        device = dbus.Interface(self.bus.get_object("org.bluez", device_path), "org.bluez.Device1")
        try:
            properties = dbus.Interface(device, "org.freedesktop.DBus.Properties")
            return properties.Get("org.bluez.Device1", "Connected")
        except dbus.DBusException as e:
            print(f"Error checking connection status: {e}")
            return False

    def connect_device(self, device_path):
        device = dbus.Interface(self.bus.get_object("org.bluez", device_path), "org.bluez.Device1")
        try:
            device.Connect()
            print(f"Attempting to connect to device: {device_path}")
        except dbus.DBusException as e:
            print(f"Failed to connect to device: {e}")

    def lock_door(self):
        if not self.door_locked:
            GPIO.output(DOOR_LOCK_PIN, GPIO.LOW)
            self.door_locked = True
            print("Locking the door...")
            print("Door is LOCKED")

    def unlock_door(self):
        if self.door_locked:
            GPIO.output(DOOR_LOCK_PIN, GPIO.HIGH)
            self.door_locked = False
            print("Unlocking the door...")
            print("Door is UNLOCKED")

    def monitor_paired_devices(self):
        if self.monitoring_paused:
            return

        self.refresh_managed_objects()
        paired_devices = self.list_paired_devices()
       
        
        for device_address, device_path in paired_devices:
            connected = self.device_status(device_path)

            if connected and device_address not in self.connected_devices:
                print(f"Device {device_address} is connected.")
                self.connected_devices.add(device_address)
                if self.door_locked:
                    self.unlock_door()
                    self.start_auto_lock_timer()
                break

            elif not connected and device_address in self.connected_devices:
                print(f"Device {device_address} is disconnected.")
                self.connected_devices.remove(device_address)
                if not self.door_locked:
                    self.lock_door()
                break

            # New logic: If device is paired but not connected, attempt to connect
            elif not connected:
                print(f"Device {device_address} is paired but not connected. Attempting to connect...")
                self.connect_device(device_path)

    def start_auto_lock_timer(self):
        if self.auto_lock_timer:
            self.auto_lock_timer.cancel()
        print(f"Starting {self.auto_lock_duration}-second timer for automatic door locking...")
        self.auto_lock_timer = threading.Timer(self.auto_lock_duration, self.lock_door)
        self.auto_lock_timer.start()

    def pause_monitoring(self):
        self.monitoring_paused = True
        print("Paired device monitoring paused for 1 minute.")
        threading.Timer(60, self.resume_monitoring).start()

    def resume_monitoring(self):
        self.monitoring_paused = False
        self.monitor_paired_devices()
        
    def unpair_device(self, device_address):
        """Unpair the device specified by the device address."""
        paired_devices = self.list_paired_devices()
        for address, path in paired_devices:
            if address.lower() == device_address.lower():
                adapter_path = "/org/bluez/hci0"  # Default adapter path
                adapter = dbus.Interface(self.bus.get_object("org.bluez", adapter_path), "org.bluez.Adapter1")
                try:
                    adapter.RemoveDevice(path)
                    print(f"Device {device_address} unpaired successfully.")
                    return
                except dbus.DBusException as e:
                    print(f"Failed to unpair device: {e}")
                    return
        print(f"Device {device_address} not found in paired devices.")


#===========================================================================================================
#                       Application Register Code 
#===========================================================================================================
class Application(dbus.service.Object):
    """
    org.bluez.GattApplication1 interface implementation
    """
    def __init__(self, bus,service):
        self.path = '/'
        self.services = []
        dbus.service.Object.__init__(self, bus, self.path)
        self.add_service(service)

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_service(self, service):
        self.services.append(service)

    @dbus.service.method(DBUS_OM_IFACE, out_signature='a{oa{sa{sv}}}')
    def GetManagedObjects(self):
        response = {}
        print('GetManagedObjects')

        for service in self.services:
            response[service.get_path()] = service.get_properties()
            chrcs = service.get_characteristics()
            for chrc in chrcs:
                response[chrc.get_path()] = chrc.get_properties()
                descs = chrc.get_descriptors()
                for desc in descs:
                    response[desc.get_path()] = desc.get_properties()

        return response


class Service(dbus.service.Object):
    """
    org.bluez.GattService1 interface implementation
    """
    PATH_BASE = '/org/bluez/example/service'

    def __init__(self, bus, index, uuid, primary):
        self.path = self.PATH_BASE + str(index)
        self.bus = bus
        self.uuid = uuid
        self.primary = primary
        self.characteristics = []
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        return {
                GATT_SERVICE_IFACE: {
                        'UUID': self.uuid,
                        'Primary': self.primary,
                        'Characteristics': dbus.Array(
                                self.get_characteristic_paths(),
                                signature='o')
                }
        }

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_characteristic(self, characteristic):
        self.characteristics.append(characteristic)

    def get_characteristic_paths(self):
        result = []
        for chrc in self.characteristics:
            result.append(chrc.get_path())
        return result

    def get_characteristics(self):
        return self.characteristics

    @dbus.service.method(DBUS_PROP_IFACE,
                         in_signature='s',
                         out_signature='a{sv}')
    def GetAll(self, interface):
        if interface != GATT_SERVICE_IFACE:
            raise InvalidArgsException()

        return self.get_properties()[GATT_SERVICE_IFACE]


class Characteristic(dbus.service.Object):
    """
    org.bluez.GattCharacteristic1 interface implementation
    """
    def __init__(self, bus, index, uuid, flags, service):
        self.path = service.path + '/char' + str(index)
        self.bus = bus
        self.uuid = uuid
        self.service = service
        self.flags = flags
        self.descriptors = []
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        return {
                GATT_CHRC_IFACE: {
                        'Service': self.service.get_path(),
                        'UUID': self.uuid,
                        'Flags': self.flags,
                        'Descriptors': dbus.Array(
                                self.get_descriptor_paths(),
                                signature='o')
                }
        }

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_descriptor(self, descriptor):
        self.descriptors.append(descriptor)

    def get_descriptor_paths(self):
        result = []
        for desc in self.descriptors:
            result.append(desc.get_path())
        return result

    def get_descriptors(self):
        return self.descriptors

    @dbus.service.method(DBUS_PROP_IFACE,
                         in_signature='s',
                         out_signature='a{sv}')
    def GetAll(self, interface):
        if interface != GATT_CHRC_IFACE:
            raise InvalidArgsException()

        return self.get_properties()[GATT_CHRC_IFACE]

    @dbus.service.method(GATT_CHRC_IFACE,
                        in_signature='a{sv}',
                        out_signature='ay')
    def ReadValue(self, options):
        print('Default ReadValue called, returning error')
        raise NotSupportedException()

    @dbus.service.method(GATT_CHRC_IFACE, in_signature='aya{sv}')
    def WriteValue(self, value, options):
        print('Default WriteValue called, returning error')
        raise NotSupportedException()

    @dbus.service.method(GATT_CHRC_IFACE)
    def StartNotify(self):
        print('Default StartNotify called, returning error')
        raise NotSupportedException()

    @dbus.service.method(GATT_CHRC_IFACE)
    def StopNotify(self):
        print('Default StopNotify called, returning error')
        raise NotSupportedException()

    @dbus.service.signal(DBUS_PROP_IFACE,
                         signature='sa{sv}as')
    def PropertiesChanged(self, interface, changed, invalidated):
        pass


class Descriptor(dbus.service.Object):
    """
    org.bluez.GattDescriptor1 interface implementation
    """
    def __init__(self, bus, index, uuid, flags, characteristic):
        self.path = characteristic.path + '/desc' + str(index)
        self.bus = bus
        self.uuid = uuid
        self.flags = flags
        self.chrc = characteristic
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        return {
                GATT_DESC_IFACE: {
                        'Characteristic': self.chrc.get_path(),
                        'UUID': self.uuid,
                        'Flags': self.flags,
                }
        }

    def get_path(self):
        return dbus.ObjectPath(self.path)

    @dbus.service.method(DBUS_PROP_IFACE,
                         in_signature='s',
                         out_signature='a{sv}')
    def GetAll(self, interface):
        if interface != GATT_DESC_IFACE:
            raise InvalidArgsException()

        return self.get_properties()[GATT_DESC_IFACE]

    @dbus.service.method(GATT_DESC_IFACE,
                        in_signature='a{sv}',
                        out_signature='ay')
    def ReadValue(self, options):
        print ('Default ReadValue called, returning error')
        raise NotSupportedException()

    @dbus.service.method(GATT_DESC_IFACE, in_signature='aya{sv}')
    def WriteValue(self, value, options):
        
        print('Default WriteValue called, returning error')
        
        raise NotSupportedException()


class CustomMessageService(Service):
    """
    Custom Message Service for sending and receiving messages.
    """
    SERVICE_UUID = '12345678-1234-1234-1234-1234567890ab'  # Custom Service UUID

    def __init__(self, bus, index):
        Service.__init__(self, bus, index, self.SERVICE_UUID, True)
        self.add_characteristic(MessageCharacteristicChrc(bus, 0, self))
       


#===========================================================================================================
# Custom Message Characteristic for Hardcoded
#===========================================================================================================       

class MessageCharacteristicChrc(Characteristic):
    MSG_CHRC_UUID = 'abcd1234-ab12-cd34-ef56-abcdef123456'  # Custom Message Characteristic UUID

    def __init__(self, bus, index, service):
        Characteristic.__init__(
            self, bus, index,
            self.MSG_CHRC_UUID,
            ['write', 'notify', 'read'],  # Allow write, notify, and read
            service
        )
        self.notifying = False
        # Set initial state for the door and LED
        self.lock_door()
        
    def lock_door(self):
        """Lock the door and turn OFF the LED."""
        GPIO.output(DOOR_LOCK_PIN, GPIO.LOW)
        print("Locking the door with Hardcoded")
        print("Door is LOCKED")
    
    def unlock_door(self):
        """Unlock the door and turn ON the LED."""
        GPIO.output(DOOR_LOCK_PIN, GPIO.HIGH)
        print("Unlocking the door with Hardcoded")
        print("Door is UNLOCKED")
        time.sleep(auto_lock_duration)
        self.lock_door()
    
    def WriteValue(self, value, options):
        # Convert received bytes to a string
        password_received = ''.join(chr(b) for b in value)
        print(f"Received password: {password_received}")

        # Hardcoded password for comparison
        hardcoded_password = "1234"

        # Compare passwords and set notification value
        if password_received == hardcoded_password:
            self.value = "Matched"
            self.unlock_door()  # Unlock the door and turn ON the LED
        else:
            self.value = "Not matched"
            self.lock_door()  # Lock the door and turn OFF the LED
    
        # Notify clients with the comparison result
        # self.notify_clients()

    def ReadValue(self, options):
        # Return the current status message to the client
        print(f"ReadValue called, returning: {self.value}")
        return self.value.encode('utf-8')  # Return bytes
    
    def notify_clients(self):
        value_bytes = self.value.encode('utf-8')  # Encode the string to bytes
        print(value_bytes)
        self.PropertiesChanged(GATT_CHRC_IFACE, {'Value': self.value}, [])
        print(f"Notification sent: {self.value}")
    
    def StartNotify(self):
        if self.notifying:
            print('Already notifying, nothing to do')
            return

        self.notifying = True
        self.notify_clients()

    def StopNotify(self):
        if not self.notifying:
            print('Not notifying, nothing to do')
            return

        self.notifying = False   
        

#===========================================================================================================
# Custom Message Characteristic for Cloud 
#===========================================================================================================
class CustomMessageService_Cloud(Service):
    """
    Custom Message Service for sending and receiving messages.
    """
    SERVICE_UUID1 = '12345678-1234-1234-1234-1234567890ac'  # Custom Service UUID

    def __init__(self, bus, index):
        Service.__init__(self, bus, index, self.SERVICE_UUID1, True)
        self.add_characteristic(MessageCharacteristicChrc_Cloud(bus, 0, self))

class MessageCharacteristicChrc_Cloud(Characteristic):
    MSG_CHRC_UUID1 = 'abcd1234-ab12-cd34-ef56-abcdef123457'  # Custom Message Characteristic UUID

    def __init__(self, bus, index, service):
        Characteristic.__init__(
            self, bus, index,
            self.MSG_CHRC_UUID1,
            ['write', 'notify', 'read'],  # Allow write, notify, and read
            service
        )
        self.notifying = False
    
        # Set initial state for the door and LED
        self.lock_door()
        
    def lock_door(self):
        """Lock the door and turn OFF the LED."""
        GPIO.output(DOOR_LOCK_PIN, GPIO.LOW)
        print("Locking the door with Cloud.")
        print("Door is LOCKED")
    
    def unlock_door(self):
        """Unlock the door and turn ON the LED."""
        GPIO.output(DOOR_LOCK_PIN, GPIO.HIGH)
        print("Unlocking the door with Cloud.")
        print("Door is UNLOCKED")
        print(f'Starting {auto_lock_duration}-second timer for automatic door locking...')
        time.sleep(auto_lock_duration)
        self.lock_door()
        
            
    def WriteValue(self, value, options):
        # Convert received bytes to a string
        password_received = ''.join(chr(b) for b in value)
        print(f"Received password: {password_received}")

        # Cloud-based password for comparison (use the actual cloud password)
        cloud_password = get_password_from_thingspeak()  # Replace with actual cloud password

        # Compare passwords and set notification value
        if password_received == cloud_password:
            self.value = "Matched"
            self.unlock_door()
        else:
            self.value = "Not matched"
            self.lock_door()
    
        # Notify clients with the comparison result
        # self.notify_clients()

    def ReadValue(self, options):
        # Return the current status message to the client
        print(f"ReadValue called, returning: {self.value}")
        return self.value.encode('utf-8')  # Return bytes
    
    def notify_clients(self):
        value_bytes = self.value.encode('utf-8')  # Encode the string to bytes
        print(value_bytes)
        self.PropertiesChanged(GATT_CHRC_IFACE, {'Value': self.value}, [])
        print(f"Notification sent: {self.value}")
    
    def StartNotify(self):
        if self.notifying:
            print('Already notifying, nothing to do')
            return

        self.notifying = True
        self.notify_clients()

    def StopNotify(self):
        if not self.notifying:
            print('Not notifying, nothing to do')
            return

        self.notifying = False 

#-----------------------------------------RandomCloud----------------------------

class CustomMessageService_RandomCloud(Service):
    """
    Custom Message Service for sending and receiving messages.
    """
    SERVICE_UUID2 = '12345678-1234-1234-1234-1234567890de'  # Custom Service UUID

    def __init__(self, bus, index):
        Service.__init__(self, bus, index, self.SERVICE_UUID2, True)
        self.add_characteristic(MessageCharacteristicChrc_RandomCloud(bus, 0, self))

class MessageCharacteristicChrc_RandomCloud(Characteristic):
    MSG_CHRC_UUID2 = 'abcd1234-ab12-cd34-ef56-abcdef123458'  # Custom Message Characteristic UUID

    def __init__(self, bus, index, service):
        Characteristic.__init__(
            self, bus, index,
            self.MSG_CHRC_UUID2,
            ['write', 'notify', 'read'],  # Allow write, notify, and read
            service
        )
        self.notifying = False
    
        # Set initial state for the door and LED
        self.lock_door()
        
    def lock_door(self):
        """Lock the door and turn OFF the LED."""
        GPIO.output(DOOR_LOCK_PIN, GPIO.LOW)
        print("Locking the door with Cloud.")
        print("Door is LOCKED")
    
    def unlock_door(self):
        """Unlock the door and turn ON the LED."""
        GPIO.output(DOOR_LOCK_PIN, GPIO.HIGH)
        print("Unlocking the door with Cloud.")
        print("Door is UNLOCKED")
        print(f'Starting {auto_lock_duration}-second timer for automatic door locking...')
        time.sleep(auto_lock_duration)
        self.lock_door()

    def WriteValue(self, value, options):
    # Convert received bytes to a string
        password_received = ''.join(chr(b) for b in value)
        print(f"Received password: {password_received}")

    # Fetch the cloud-based password for comparison
        cloud_password = get_password_from_thingspeak()  # Fetch the password from ThingSpeak

        if not cloud_password:
            print("Error: No password fetched from ThingSpeak.")
            self.value = "Error".encode('utf-8')
            return  # Exit early on error

    # Compare the received password with the cloud password
        if password_received == cloud_password:
            self.value="Matched"
            #print("Password matched!")
            self.unlock_door()  # Unlock the door
        # Generate and update a new password in the cloud
            new_password = generate_unique_password()
            update_cloud_password(new_password)
            cloud_password = new_password

        # Wait for 5 seconds before locking the door again
        #time.sleep(5)
            #self.lock_door()  # Lock the door again after the wait
            #self.value = "Matched".encode('utf-8')
        else:
            self.value = "Not Matched"
            self.lock_door()
            #print("Password not matched.")
            #self.value = "Not Matched".encode('utf-8')
        
        cloud_password = get_password_from_thingspeak()
  

        # Notify clients with the comparison result
        # self.notify_clients()

    def ReadValue(self, options):
        # Return the current status message to the client
        print(f"ReadValue called, returning: {self.value}")
        return self.value.encode('utf-8')  # Return bytes
    
    def notify_clients(self):
        value_bytes = self.value.encode('utf-8')  # Encode the string to bytes
        print(value_bytes)
        self.PropertiesChanged(GATT_CHRC_IFACE, {'Value': self.value}, [])
        print(f"Notification sent: {self.value}")
    
    def StartNotify(self):
        if self.notifying:
            print('Already notifying, nothing to do')
            return

        self.notifying = True
        self.notify_clients()

    def StopNotify(self):
        if not self.notifying:
            print('Not notifying, nothing to do')
            return

        self.notifying = False  


def register_app_cb():
    print('GATT application registered')

def register_app_error_cb(error):
    print('Failed to register application: ' + str(error))
    mainloop.quit()

def find_adapter(bus):
    remote_om = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, '/'),
                               DBUS_OM_IFACE)
    objects = remote_om.GetManagedObjects()

    for o, props in objects.items():
        if GATT_MANAGER_IFACE in props.keys():
            return o

    return None

def register_app_cb():
    print('GATT application registered')


def register_app_error_cb(error):
    print('Failed to register application: ' + str(error))
    mainloop.quit()


def find_adapter(bus):
    remote_om = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, '/'),
                               DBUS_OM_IFACE)
    objects = remote_om.GetManagedObjects()

    for o, props in objects.items():
        if GATT_MANAGER_IFACE in props.keys():
            return o

    return None

#===========================================================================================================
# Advertisement Class 
#===========================================================================================================

class Advertisement(dbus.service.Object):
    PATH_BASE = '/org/bluez/example/advertisement'

    def __init__(self, bus, index, advertising_type):
        self.path = self.PATH_BASE + str(index)
        self.bus = bus
        self.ad_type = advertising_type
        self.service_uuids = None
        self.manufacturer_data = None
        self.solicit_uuids = None
        self.service_data = None
        self.local_name = None
        self.include_tx_power = False
        self.data = None
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        properties = dict()
        properties['Type'] = self.ad_type
        if self.service_uuids is not None:
            properties['ServiceUUIDs'] = dbus.Array(self.service_uuids,
                                                    signature='s')
        if self.solicit_uuids is not None:
            properties['SolicitUUIDs'] = dbus.Array(self.solicit_uuids,
                                                    signature='s')
        if self.manufacturer_data is not None:
            properties['ManufacturerData'] = dbus.Dictionary(
                self.manufacturer_data, signature='qv')
        if self.service_data is not None:
            properties['ServiceData'] = dbus.Dictionary(self.service_data,
                                                        signature='sv')
        if self.local_name is not None:
            properties['LocalName'] = dbus.String(self.local_name)
        if self.include_tx_power:
            properties['Includes'] = dbus.Array(["tx-power"], signature='s')

        if self.data is not None:
            properties['Data'] = dbus.Dictionary(
                self.data, signature='yv')
        return {LE_ADVERTISEMENT_IFACE: properties}

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_service_uuid(self, uuid):
        if not self.service_uuids:
            self.service_uuids = []
        self.service_uuids.append(uuid)

    def add_solicit_uuid(self, uuid):
        if not self.solicit_uuids:
            self.solicit_uuids = []
        self.solicit_uuids.append(uuid)

    def add_manufacturer_data(self, manuf_code, data):
        if not self.manufacturer_data:
            self.manufacturer_data = dbus.Dictionary({}, signature='qv')
        self.manufacturer_data[manuf_code] = dbus.Array(data, signature='y')

    def add_service_data(self, uuid, data):
        if not self.service_data:
            self.service_data = dbus.Dictionary({}, signature='sv')
        self.service_data[uuid] = dbus.Array(data, signature='y')

    def add_local_name(self, name):
        if not self.local_name:
            self.local_name = ""
        self.local_name = dbus.String(name)

    def add_data(self, ad_type, data):
        if not self.data:
            self.data = dbus.Dictionary({}, signature='yv')
        self.data[ad_type] = dbus.Array(data, signature='y')

    @dbus.service.method(DBUS_PROP_IFACE,
                         in_signature='s',
                         out_signature='a{sv}')
    def GetAll(self, interface):
        print('GetAll')
        if interface != LE_ADVERTISEMENT_IFACE:
            raise InvalidArgsException()
        print('returning props')
        return self.get_properties()[LE_ADVERTISEMENT_IFACE]

    @dbus.service.method(LE_ADVERTISEMENT_IFACE,
                         in_signature='',
                         out_signature='')
    def Release(self):
        print('%s: Released!' % self.path)

#===========================================================================================================
# TestAdvertisement Class 
#===========================================================================================================


class TestAdvertisement(Advertisement):

    def __init__(self, bus, index):
        Advertisement.__init__(self, bus, index, 'peripheral')
        self.add_service_uuid('180D')
        self.add_service_uuid('180F')
        self.add_manufacturer_data(0xffff, [0x00, 0x01, 0x02, 0x03])
        self.add_service_data('9999', [0x00, 0x01, 0x02, 0x03, 0x04])
        self.add_local_name('RPI_BLE')
        self.include_tx_power = True
        self.add_data(0x26,[0x01, 0x01, 0x00])


def register_ad_cb():
    print('Advertisement registered')


def register_ad_error_cb(error):
    print('Failed to register advertisement: ' + str(error))
    mainloop.quit()


def find_adapter(bus):
    remote_om = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, '/'),
                               DBUS_OM_IFACE)
    objects = remote_om.GetManagedObjects()

    for o, props in objects.items():
        if LE_ADVERTISING_MANAGER_IFACE in props:
            return o

    return None

#===========================================================================================================
#   Door Code Program Feature by using nRF connect Mobile application 
#===========================================================================================================

def hard_code():
    global mainloop, app, service_manager, ad_manager, test_advertisement

    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()

    adapter = find_adapter(bus)
    if not adapter:
        print('GattManager1 interface not found')
        return None

    service_manager = dbus.Interface(
        bus.get_object(BLUEZ_SERVICE_NAME, adapter),
        GATT_MANAGER_IFACE
    )

    application_unregister()  # Clean up the previous application instance
    service = CustomMessageService(bus, 0)
    app = Application(bus,service)  # Create a new instance of Application
    mainloop = GLib.MainLoop()

    print('Registering GATT application...')
    service_manager.RegisterApplication(app.get_path(), {},
                                        reply_handler=register_app_cb,
                                        error_handler=register_app_error_cb)

    adapter_props = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, adapter),
                                   "org.freedesktop.DBus.Properties")
    adapter_props.Set("org.bluez.Adapter1", "Powered", dbus.Boolean(1))

    ad_manager = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, adapter),
                                LE_ADVERTISING_MANAGER_IFACE)
    test_advertisement = TestAdvertisement(bus, 0)

    ad_manager.RegisterAdvertisement(test_advertisement.get_path(), {},
                                     reply_handler=register_ad_cb,
                                     error_handler=register_ad_error_cb)

    return mainloop

def cloud_code():
    global mainloop, app, service_manager, ad_manager, test_advertisement

    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()

    adapter = find_adapter(bus)
    if not adapter:
        print('GattManager1 interface not found')
        return None

    service_manager = dbus.Interface(
        bus.get_object(BLUEZ_SERVICE_NAME, adapter),
        GATT_MANAGER_IFACE
    )

    application_unregister()  # Clean up the previous application instance
    service = CustomMessageService_Cloud(bus, 0)
    app = Application(bus,service)  # Create a new instance of Application
    mainloop = GLib.MainLoop()

    print('Registering GATT application...')
    service_manager.RegisterApplication(app.get_path(), {},
                                        reply_handler=register_app_cb,
                                        error_handler=register_app_error_cb)

    adapter_props = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, adapter),
                                   "org.freedesktop.DBus.Properties")
    adapter_props.Set("org.bluez.Adapter1", "Powered", dbus.Boolean(1))

    ad_manager = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, adapter),
                                LE_ADVERTISING_MANAGER_IFACE)
    test_advertisement = TestAdvertisement(bus, 0)

    ad_manager.RegisterAdvertisement(test_advertisement.get_path(), {},
                                     reply_handler=register_ad_cb,
                                     error_handler=register_ad_error_cb)

    return mainloop

def random_cloud_code():
    global mainloop, app, service_manager, ad_manager, test_advertisement

    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()

    adapter = find_adapter(bus)
    if not adapter:
        print('GattManager1 interface not found')
        return None

    service_manager = dbus.Interface(
        bus.get_object(BLUEZ_SERVICE_NAME, adapter),
        GATT_MANAGER_IFACE
    )

    application_unregister()  # Clean up the previous application instance
    service = CustomMessageService_RandomCloud(bus, 0)
    app = Application(bus,service)  # Create a new instance of Application
    mainloop = GLib.MainLoop()

    print('Registering GATT application...')
    service_manager.RegisterApplication(app.get_path(), {},
                                        reply_handler=register_app_cb,
                                        error_handler=register_app_error_cb)

    adapter_props = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, adapter),
                                   "org.freedesktop.DBus.Properties")
    adapter_props.Set("org.bluez.Adapter1", "Powered", dbus.Boolean(1))

    ad_manager = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, adapter),
                                LE_ADVERTISING_MANAGER_IFACE)
    test_advertisement = TestAdvertisement(bus, 0)

    ad_manager.RegisterAdvertisement(test_advertisement.get_path(), {},
                                     reply_handler=register_ad_cb,
                                     error_handler=register_ad_error_cb)

    return mainloop

def unregister_adv():
    global ad_manager, test_advertisement
    if ad_manager and test_advertisement:
        ad_manager.UnregisterAdvertisement(test_advertisement.get_path())
        dbus.service.Object.remove_from_connection(test_advertisement)

def application_unregister():
    global service_manager, app

    if app is not None:
        print("Cleaning up previous application instance...")
        try:
            if service_manager:
                service_manager.UnregisterApplication(app.get_path(), reply_handler=None, error_handler=None)
                print(f"Unregistered application at path: {app.get_path()}")
            dbus.service.Object.remove_from_connection(app)
            dbus.service.Object.remove_from_connection(app.services[0])
            dbus.service.Object.remove_from_connection(app.services[0].characteristics[0])
            unregister_adv()
        except Exception as e:
            print(f"Error during unregistration: {e}")


# Assuming `BluetoothManager` and `hard_code` are implemented elsewhere
# from your_bluetooth_module import BluetoothManager, hard_code, cleanup_gpio, application_unregister
def feature1(auto_lock_duration):
    print("Starting Feature 1 of New Pair devices")
    bt_manager = BluetoothManager_pair()
    
    try:
        # List devices after discovery
        print("Available Bluetooth devices:")
        devices = bt_manager.list_devices()
        for address, path, paired, connected in devices:
            print(f"Address: {address}, Path: {path}, Paired: {paired}, Connected: {connected}")

        # Pair with a specific device
        device_address = input("Enter the device address to pair (e.g., XX:XX:XX:XX:XX:XX): ")
        bt_manager.pair_device(device_address)

        # Close the bluetoothctl process
        bt_manager.close()
            
    except KeyboardInterrupt:
        print("Exiting feature 2...")
        
def feature2(auto_lock_duration):
    print("Starting Feature 2 of Pair Devices with auto lock duration")
    manager = BluetoothManager(auto_lock_duration)
    
    try:
        while True:
            manager.monitor_paired_devices()
            time.sleep(5)
    except KeyboardInterrupt:
        print("Exiting feature 2...")

def feature3():
    print("Starting Feature 3 Hard Door Code")
    mainloop = hard_code()

    if mainloop is not None:
        try:
            mainloop.run()
        except KeyboardInterrupt:
            print("Caught KeyboardInterrupt, exiting...")
        finally:
            if mainloop.is_running():
                mainloop.quit()
                application_unregister()
            cleanup_gpio()
            print('Cleanup actions completed.')
            
def feature4():
    print("Starting Feature 4 Cloud Based IOT Code")
    mainloop = cloud_code()

    if mainloop is not None:
        try:
            mainloop.run()
        except KeyboardInterrupt:
            print("Caught KeyboardInterrupt, exiting...")
        finally:
            if mainloop.is_running():
                mainloop.quit()
                application_unregister()
            cleanup_gpio()
            print('Cleanup actions completed.')

def feature5():
    print("Starting Feature 5 Random_Cloud Based IOT Code")
    mainloop = random_cloud_code()

    if mainloop is not None:
        try:
            mainloop.run()
        except KeyboardInterrupt:
            print("Caught KeyboardInterrupt, exiting...")
        finally:
            if mainloop.is_running():
                mainloop.quit()
                application_unregister()
            cleanup_gpio()
            print('Cleanup actions completed.')

def feature6(auto_lock_duration):
    print("Starting Feature 6 of UnPair Devices with auto lock duration")
    manager = BluetoothManager(auto_lock_duration)
    print(manager.list_paired_devices())
    device_address = input("Enter the device address to unpair (e.g., XX:XX:XX:XX:XX:XX): ")
    
    try:
        manager.unpair_device(device_address)
        time.sleep(5)
    except KeyboardInterrupt:
        print("Exiting feature 6...")

def main():
    # Create the argument parser
    parser = argparse.ArgumentParser(description="Smart Lock Bluetooth Manager CLI")
    
    # Add subcommands (features)
    subparsers = parser.add_subparsers(dest='command', help="Available commands")
    
    # Subcommand for Feature 1 (Pair Devices)
    parser_feature1 = subparsers.add_parser('1', help="New Pair Devices")
    parser_feature1.add_argument('auto_lock_duration', type=int, help="Auto lock duration in seconds")
    
    # Subcommand for Feature 2 (Pair Devices)
    parser_feature2 = subparsers.add_parser('2', help="Pair Devices with auto lock duration")
    parser_feature2.add_argument('auto_lock_duration', type=int, help="Auto lock duration in seconds")
    
    # Subcommand for Feature 3 (Hard Door Code)
    parser_feature3 = subparsers.add_parser('3', help="Hard Door Code execution")
    parser_feature3.add_argument('auto_lock_duration', type=int, help="Auto lock duration in seconds")
    
    # Subcommand for Feature 4 (Cloud Based IOT Code )
    parser_feature4 = subparsers.add_parser('4', help="Cloud Based IOT Code execution")
    parser_feature4.add_argument('auto_lock_duration', type=int, help="Auto lock duration in seconds")

    # Subcommand for Feature 5 (Random_Cloud Based IOT Code )
    parser_feature5 = subparsers.add_parser('5', help="Cloud Based IOT Code execution")
    parser_feature5.add_argument('auto_lock_duration', type=int, help="Auto lock duration in seconds")
    
    
    # Subcommand for Feature 6 (Unpair )
    parser_feature6 = subparsers.add_parser('6', help="unpair Code execution")
    parser_feature6.add_argument('auto_lock_duration', type=int, help="Auto lock duration in seconds")
    
    # Add an 'exit' option
    subparsers.add_parser('exit', help="Exit the program")
    
    # Parse the arguments
    args = parser.parse_args()
    global auto_lock_duration
    auto_lock_duration = args.auto_lock_duration 
    if args.command == '1':
        feature1(args.auto_lock_duration)
        
    elif args.command == '2':
        feature2(args.auto_lock_duration)
    
    elif args.command == '3':
        feature3()
    
    elif args.command == '4':
        feature4()
        
    elif args.command == '5':
        feature5()
     
    elif args.command == '6':
        feature6(args.auto_lock_duration)

    elif args.command == 'exit':
        print("Exiting the program...")
        return
    
    else:
        # If no valid command is provided, print the help message
        parser.print_help()

if __name__ == '__main__':
    main()
