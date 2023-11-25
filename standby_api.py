'''
Fetch the shift data from Humanity API to create a report on standby shifts
1. Create pandas df (Name, Hours, Shift, Start date, End date)
2. Request the shift data from Humanity API
    - specify period (start date to end date)
    - specify positions (api accepts id)
3. Parse the response data and insert items into pandas df
    Each data point has employees
        For each employee in this data point add and entry into df and include
            - employees name (Name)
            - employees paidtime (Hours)
            - data schedule_name (Shift)
            - data start_timestamp (Start date)
            - data end_timestamp (End date)
4. Group df by name to generate new output (Name, Number of shifts, Total hours, Weekday hours, Weekend hours)
5. Export the output to csv
'''
import requests
import json
import datetime

# Constants and configurations
AUTH_URL = 'https://www.humanity.com/oauth2/token.php'
API_BASE_URL = 'https://www.humanity.com/api/v2'
CREDENTIALS_FILE = './auth/credentials.json'

def get_access_token(credentials_file):
    # Retrieve access token using provided credentials
    with open(credentials_file) as json_file:
        credentials = json.load(json_file)
    
    response = requests.post(url=AUTH_URL, data=credentials)
    return json.loads(response.text)['access_token']


def get_shifts(start_date, end_date, access_token, positions):
    # Format URL parameters
    schedule = ', '.join(positions.keys())
    params = {
        'start_date': str(start_date),
        'end_date': str(end_date),
        'mode': 'schedule',
        'schedule': schedule,
        'access_token': access_token
    }

    # Construct API URL
    url = f'{API_BASE_URL}/shifts'
    headers = {"accept": "application/json"}

    # Get shift data
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to retrieve shifts. Status code: {response.status_code}")
        return None


if __name__ == '__main__':
    access_token = get_access_token(CREDENTIALS_FILE)
    start_date = datetime.date(2024, 2, 4)
    end_date = datetime.date(2024, 2, 5)
    positions = {'3110230': 'Cisco', '3110228': 'T1', '3110229': 'T2'}

    shifts_data = get_shifts(start_date, end_date, access_token, positions)
    if shifts_data:
        # Process shifts_data as needed
        print(shifts_data)
    else:
        # Handle failed API request
        pass
