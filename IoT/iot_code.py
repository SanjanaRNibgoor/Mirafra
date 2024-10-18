"# system iot code" 
import requests
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

