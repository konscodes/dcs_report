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

## TODO
# Add break column if shifts hours <> employee hours 
# Add weekend hours adjusted to shift report to account for breaks
# Overview report with adjusted hours


import datetime
import json

import pandas as pd
import requests

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


def parse_data(shifts_data):
    data_list = []
    for shift in shifts_data['data']:
        shift_start = shift['start_timestamp']
        shift_end = shift['end_timestamp']
        shift_name = shift['schedule_name']
        
        for employee in shift['employees']:
            employee_name = employee['name']
            employee_hours = employee['paidtime']
            
            data_list.append({
                'Name': employee_name,
                'Hours': employee_hours,
                'Shift': shift_name,
                'Start date': shift_start,
                'End date': shift_end
            })
    return pd.DataFrame(data_list)


def calculate_weekday_weekend_hours(start_date, end_date):
    weekday_hours = []
    weekend_hours = []

    for i in range(len(start_date)):
        current_start_date = pd.to_datetime(start_date[i])
        current_end_date = pd.to_datetime(end_date[i])

        if current_start_date.weekday() < 5 and current_end_date.weekday() < 5:  # Both within weekdays
            weekday_hours.append((current_end_date - current_start_date).seconds / 3600)
            weekend_hours.append(0)
        elif current_start_date.weekday() >= 5 and current_end_date.weekday() >= 5:  # Both within weekends
            weekend_hours.append((current_end_date - current_start_date).seconds / 3600)
            weekday_hours.append(0)
        else:  # Shift spans across weekend and weekdays
            midnight = current_start_date.replace(hour=0, minute=0, second=0)
            if current_start_date.weekday() < 5:  # Shift starts on weekday
                weekday_hours.append((midnight - current_start_date).seconds / 3600)
                weekend_hours.append((current_end_date - midnight).seconds / 3600)
            else:  # Shift starts on weekend
                weekend_hours.append((midnight - current_start_date).seconds / 3600)
                weekday_hours.append((current_end_date - midnight).seconds / 3600)

    return weekday_hours, weekend_hours


if __name__ == '__main__':
    access_token = get_access_token(CREDENTIALS_FILE)
    start_date = datetime.date(2024, 2, 4)
    end_date = datetime.date(2024, 2, 5)
    positions = {'3110230': 'Cisco', '3110228': 'T1', '3110229': 'T2'}

    shifts_data = get_shifts(start_date, end_date, access_token, positions)
    if shifts_data:
        # Process shifts_data as needed
        shift_report = parse_data(shifts_data)
        print(shift_report)

        # Grouping by 'Name' and aggregating shift count and total hours
        overview_report = shift_report.groupby('Name').agg(
            Number_of_shifts=('Shift', 'count'),
            Total_hours=('Hours', 'sum')
        ).reset_index()
        print(overview_report)

        # Calculate weekday and weekend hours for each shift
        weekday_hours, weekend_hours = calculate_weekday_weekend_hours(
            shift_report['Start date'], shift_report['End date']
        )

        # Add weekday and weekend hours columns to shift_report
        shift_report['Weekday_hours'] = weekday_hours
        shift_report['Weekend_hours'] = weekend_hours
        print(shift_report)

        # Grouping by 'Name' and aggregating shift count, total hours, weekday hours, and weekend hours
        overview_report = shift_report.groupby('Name').agg(
            Number_of_shifts=('Shift', 'count'),
            Total_hours=('Hours', 'sum'),
            Total_weekday_hours=('Weekday_hours', 'sum'),
            Total_weekend_hours=('Weekend_hours', 'sum')
        ).reset_index()

        print(overview_report)
    else:
        # Handle failed API request
        pass
