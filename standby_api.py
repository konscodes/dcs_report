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

if __name__ == '__main__':
    ## Generate auth token
    # Open the JSON file and load credentials   
    with open('./auth/credentials.json') as json_file:
        credentials = json.load(json_file)
    oauth = 'https://www.humanity.com/oauth2/token.php'
    response = requests.post(url=oauth, data=credentials)
    auth_token = json.loads(response.text)['access_token']

    # Set request parameters
    start_date = datetime.date(2024, 2, 4)
    end_date = datetime.date(2024, 2, 5)
    
    positions = {'3110230': 'Cisco', '203110228': 'T1', '203110229': 'T2'}
    schedule = '%2C%'.join(pos_id for pos_id in positions)
    
    api = f'https://www.humanity.com/api/v2/shifts?'
    parameters = f'start_date={start_date}&end_date={end_date}&mode=schedule&schedule={schedule}&access_token={auth_token}'
    url = api + parameters
    
    headers = {"accept": "application/json"}
    
    # Get shift data
    shifts = requests.get(url, headers)