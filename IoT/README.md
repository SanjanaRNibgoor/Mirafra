# IoT Communication with ThingSpeak

## Overview
This document provides details about the Python code used to communicate with the ThingSpeak platform in the Smart Door Lock System project.

## Purpose
The Python code enables the Raspberry Pi to send and receive password data to/from ThingSpeak, facilitating real-time updates and monitoring of access attempts.

## Key Functions
1. **Sending Data to ThingSpeak**
   - Utilizes an HTTP GET request to send password data from the Raspberry Pi to ThingSpeak.
   - The data is sent using the **status** tab, not any specific fields.
   - Example code snippet:
     ```python
     import requests
     
     def send_password_to_thingspeak(password):
         url = f"https://api.thingspeak.com/update?api_key=YOUR_API_KEY&status={password}"
         response = requests.get(url)
         return response.status_code
     ```

2. **Receiving Data from ThingSpeak**
   - Fetches the latest password from the status tab in ThingSpeak to compare with user input.
   - Example code snippet:
     ```python
     def get_latest_password():
         url = "https://api.thingspeak.com/channels/YOUR_CHANNEL_ID/status/last.json"
         response = requests.get(url)
         return response.json()['status']
     ```

## Requirements
- `requests` library for making HTTP requests.
- `RPi.GPIO` library for GPIO control.
- Valid ThingSpeak API keys for data communication.

## Configurations/ Features Overview
- **Password Management**: The code retrieves and manages the password used for authentication.
- **Real-Time Updates**: It provides real-time updates to the cloud after successful access for Feature-5.
- **Secure Communication**: Utilizes HTTPS for secure data transmission between Raspberry Pi and ThingSpeak.
- **GPIO Control**: Controls GPIO pin 18 to provide visual feedback on the lock status (locked/unlocked).
- **Automatic Lock Timer**: Automatically re-engages the lock after a defined time following a successful unlock.

## Usage
- The Raspberry Pi runs the Python script to interact with ThingSpeak and manage the lock status via GPIO, enabling password management for the smart door lock system.
