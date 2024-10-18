# System Architecture of Smart Lock System

## Overview
This document outlines the architecture of the Smart Lock System, detailing the interaction between the components, the flow of data, and how to execute the code and operate the application.

## Components
1. **Raspberry Pi**: Acts as the central server for the smart lock.
   - Hosts the main application code to manage BLE communication and control the locking mechanism.
   - Connects to ThingSpeak for cloud-based password management.

2. **nRF Connect App**: Mobile application used by users to interact with the smart lock as a client.
   - Scans for available BLE devices.
   - Facilitates pairing and password input for unlocking.

3. **ThingSpeak**: Cloud platform used for managing password data.
   - Stores the defined password for feature-4 and updates unique passwords after each successful unlock for feature-5.
   - Provides a RESTful API for communication with the Raspberry Pi.

## Execution Instructions
1. **Running the Raspberry Pi Code**:
   - Open a terminal on the Raspberry Pi.
   - Navigate to the directory containing your Python script.
   - Execute the following command to run the code:
     ```bash
     sudo python3 file_name.py feature_no _auto_timer
     ```
   - For example, to run with feature number 1 and set a 5-second auto timer, use:
     ```bash
     sudo python3 file_name.py 1 5
     ```

2. **Using the nRF Connect App**:
   - Install the nRF Connect app on your mobile device from Google Playstore.
   - Open the app and give necessary permissions and start scanning for available BLE devices.
   - Once the Raspberry Pi is detected, connect to it.
   - Under **Custom Service**, locate the characteristic where you can read/write the password.
   - Enter the desired password and write it to the Raspberry Pi.
   - The Raspberry Pi will verify the password and respond accordingly.
   - The LED indicator on GPIO Pin 18 will visualize the status:
     - **LED On**: Door is unlocked.
     - **LED Off**: Door is locked.
   - You can read the response from the Raspberry Pi in the app to check if the password matched or not.

## Data Flow
1. **User Interaction**:
   - The user opens the nRF Connect app to scan for BLE devices.
   - The app connects to the Raspberry Pi.

2. **Password Management**:
   - The user inputs a password in the nRF Connect app.
   - The password is sent to the Raspberry Pi for verification.

3. **Verification Process**:
   - The Raspberry Pi retrieves the latest password from ThingSpeak and compares it with the user input.
   - If the password matches, the lock is activated, and the LED indicator on GPIO Pin 18 turns on.
   - The lock status is then communicated back to the ThingSpeak platform.

4. **Automatic Lock Mechanism**:
   - After unlocking, the system waits for a predefined time and automatically locks again.
   - The LED indicator turns off, reflecting the locked status.

5. **Password Update**:
   - A new random password is generated in ThingSpeak after each successful unlock.
   - The cloud is updated, ensuring the next unlock attempt requires the new password.

## GPIO Control
- **Pin 18**: Controls an LED indicator to show the lock status:
  - **LED On**: Door is unlocked.
  - **LED Off**: Door is locked.

## Configuration Overview
- **Pairing New Devices**: Users can pair new devices for access.
- **Auto Connect**: Automatically connects to paired devices within range.
- **Hardcoded Password**: Utilizes a static password for authentication.
- **Random Password Generation**: New passwords are generated in the cloud post-unlock.
- **Unpairing Devices**: Users can unpair any connected device.
- **Automatic Lock Timer**: Automatically engages the lock after a defined time.

## Future Enhancements
- Explore additional security measures.
- Expand to support multiple locks.
- Integrate with existing smart home ecosystems.