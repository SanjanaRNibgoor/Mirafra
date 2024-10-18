# Smart Door Lock System Project

## Overview
This project implements a secure smart door lock system using Raspberry Pi and Bluetooth Low Energy (BLE) technology. The system also communicates with a cloud-based platform (ThingSpeak) for real-time password management and access control.

## Technologies Used
- **Raspberry Pi**: The main server for the smart door lock system.
- **Bluetooth Low Energy (BLE)**: For secure communication with the nRF Connect app.
- **nRF Connect App**: A mobile application used to interact with the smart door lock.
- **ThingSpeak**: A cloud-based platform for managing and storing password data.

## Features
- Secure password authentication via BLE.
- Real-time communication with ThingSpeak.
- Event-driven programming for efficient responses.
- **GPIO Pin 18**: Used to control an LED that indicates the status of the lock (locked or unlocked).
- **Automatic Lock Timer**: The lock automatically re-engages after a defined time following a successful unlock.

## Configurations / Features
1. **Pairing New Devices**: Allows users to pair new devices for access.
2. **Auto Connect**: Automatically connects to paired devices within range, enabling unlocking without manual intervention.
3. **Hardcoded Password**: Uses a static password stored in the system for authentication.
4. **Hardcoded Comparison from Cloud**: Compares the input password with the one stored in ThingSpeak.
5. **Random Password Generation**: Generates a new random password in the cloud after each successful unlock.
6. **Unpairing Devices**: Enables the option to unpair any connected device from the system.

## GPIO Pin Usage
- **Pin 18**: Controls an LED indicator that shows the lock status.
  - **LED On**: Indicates that the door is unlocked.
  - **LED Off**: Indicates that the door is locked.

## Installation
1. Clone the repository.
2. Set up the Raspberry Pi with the required libraries for BLE communication and GPIO control.
3. Configure the ThingSpeak account and API keys.
4. Install the nRF Connect app from the Google Play Store on your Android device.

## Usage
- Use the nRF Connect app to scan and connect to the Raspberry Pi.
- Enter a password to unlock the smart door lock.
- The lock will automatically engage after a predefined time.
- Monitor access attempts and lock status via ThingSpeak.
