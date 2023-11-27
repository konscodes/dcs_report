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
        'mode': 'overview',
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
        shift_position = shift['schedule_name']
        shift_pos_id = shift['schedule']
        shift_title = shift['title']
        shift_hours = shift['paidtime']
        
        # Check if there are employees assigned
        if shift['employees']:
            for employee in shift['employees']:
                employee_name = employee['name']
                employee_hours = employee['paidtime']
                
                data_list.append({
                    'Name': employee_name,
                    'Position': shift_position,
                    'Pos_id': shift_pos_id,
                    'Title': shift_title,
                    'Start_date': shift_start,
                    'End_date': shift_end,
                    'Employee_hours': employee_hours,
                    'Shift_hours': shift_hours,
                })
        
        # Account for OnCall shifts
        if 'employeesOnCall' in shift:
            for employee in shift['employeesOnCall']:
                employee_name = employee['name']
                
                data_list.append({
                    'Name': employee_name,
                    'Position': shift_position,
                    'Pos_id': shift_pos_id,
                    'Title': shift_title,
                    'Start_date': shift_start,
                    'End_date': shift_end,
                    'Employee_hours': shift_hours,
                    'Shift_hours': shift_hours,
                })
    return pd.DataFrame(data_list)


def calculate_overtime(start_time, end_time):
    window_start = start_time.replace(hour=9, minute=0, second=0)
    window_end = start_time.replace(hour=18, minute=0, second=0)
    
    # If the start time is after the window end or end time is before the window start
    if start_time >= window_end or end_time <= window_start:
        return (end_time - start_time).total_seconds() / 3600  # Total hours outside the window
    
    # Calculating the duration outside the window
    if start_time < window_start:
        outside_before_start = (window_start - start_time).total_seconds() / 3600
    else:
        outside_before_start = 0
    
    if end_time > window_end:
        outside_after_end = (end_time - window_end).total_seconds() / 3600
    else:
        outside_after_end = 0
    
    overtime = outside_before_start + outside_after_end
    return overtime


def calculate_weekday_weekend_hours(start_date, end_date):
    weekday_hours = []
    weekend_hours = []
    overtime = []

    for i in range(len(start_date)):
        start = pd.to_datetime(start_date[i])
        end = pd.to_datetime(end_date[i])
        
        # Shift starts and ends within weekdays
        if start.weekday() < 5 and end.weekday() < 5:
            weekday_hours.append((end - start).seconds / 3600)
            weekend_hours.append(0)
            # Log overtime for hours outside of business start (9am) to business end (6pm)
            overtime.append(calculate_overtime(start, end))
        
        # Shift starts and ends within weekends
        elif start.weekday() >= 5 and end.weekday() >= 5:
            weekend_hours.append((end - start).seconds / 3600)
            weekday_hours.append(0)
            # Log all weekend time towards overtime
            overtime.append((end - start).seconds / 3600)
        
        # Shift spans across weekend and weekdays
        else:
            midnight = end.replace(hour=0, minute=0, second=0)
            after_midnight = (end - midnight).seconds / 3600
            before_midnight = (midnight - start).seconds / 3600
            # Shift starts on weekday and ends on weekend
            if start.weekday() < 5:
                weekday_hours.append(before_midnight)
                weekend_hours.append(after_midnight)
                # Log overtime for hours outside of business start (9am) to business end (6pm) starting from start date up till midnight
                # Log all weekend time towards overtime
                overtime.append(calculate_overtime(start, midnight) + after_midnight)
            
            # Shift starts on weekend and ends on weekday
            else:
                weekday_hours.append(after_midnight)
                weekend_hours.append(before_midnight)         
                # Log all weekend time towards overtime
                # Log overtime for hours outside of business start (9am) to business end (6pm) starting from midnight till the end date
                overtime.append(before_midnight + calculate_overtime(midnight, end))
    return weekday_hours, weekend_hours, overtime


if __name__ == '__main__':
    access_token = get_access_token(CREDENTIALS_FILE)
    start_date = datetime.date(2023, 7, 5)
    end_date = datetime.date(2023, 7, 5)
    positions = {'3110230': 'Cisco', '3110228': 'T1', '3110229': 'T2', '3110183': 'NCR 1319'}

    shifts_data = get_shifts(start_date, end_date, access_token, positions)
    if shifts_data:
        # Process shifts_data as needed
        shift_report = parse_data(shifts_data)

        # Calculate weekday and weekend hours for each shift
        weekday_hours, weekend_hours, overtime = calculate_weekday_weekend_hours(
            shift_report['Start_date'], shift_report['End_date']
        )

        # Add additional columns to shift_report
        shift_report['Break'] = shift_report['Shift_hours'] - shift_report['Employee_hours']
        # Account for missing breaks
        condition = (shift_report['Pos_id'] == '3110228') & (shift_report['Title'] == 'Morning/Day') & (shift_report['Break'] == 0)
        shift_report.loc[condition, 'Employee_hours'] -= 9.0
        shift_report.loc[condition, 'Break'] = 9.0
        
        shift_report['Weekday_hours'] = weekday_hours - shift_report['Break']
        shift_report['Weekend_hours'] = weekend_hours
        shift_report['Overtime'] = overtime
        print(shift_report)

        # Standby report
        # Grouping by 'Name' and aggregating shift count, total hours, weekday hours, and weekend hours
        standby_report = shift_report.groupby('Name').agg(
            Number_of_shifts=('Position', 'count'),
            Total_hours=('Employee_hours', 'sum'),
            Total_weekday_hours=('Weekday_hours', 'sum'),
            Total_weekend_hours=('Weekend_hours', 'sum')
        ).reset_index()
        print(standby_report)
    else:
        # Handle failed API request
        pass
