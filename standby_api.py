'''
Fetch the shift data from Humanity API to create a report on standby shifts
1. Create pandas df for shifts (Name, Position, Pos_id, Title, Start date, End date, Employee_hours, Shift_hours)
2. Request the overview of shift data from Humanity API
    - auth with API using credentials and token
    - specify period (start date to end date)
    - optionally request a position data from API to save store locally as a json
3. Parse the response data and insert items into pandas df for shifts
    Each data point has employees
        For each employee in this data point add and entry into df and include
            - employees name (Name)
            - employees paidtime (Employee_hours) hours accounting for break
            - data schedule_name (Position)
            - data schedule (Pos_id)
            - data title (Title)
            - data paidtime (Shift_hours) total hours scheduled
            - data start_timestamp (Start date)
            - data end_timestamp (End date)
4. Process shift data to separate hours
    - weekend hours
    - weekday hours
    - overtime outside business hours (9:00 to 18:00)
4. Group shifts df by name to generate a report (Name, Number of shifts, Total hours, Weekday hours, Weekend hours)
5. Export the report to csv
'''
import datetime
import json

import pandas as pd
import requests

# Constants and configurations
AUTH_URL = 'https://www.humanity.com/oauth2/token.php'
API_BASE_URL = 'https://www.humanity.com/api/v2'
CREDENTIALS_FILE = './auth/credentials.json'
POSITIONS_FILE = './output/positions.json'
OUTPUT_REPORT_PATH = './output/report_'

# Function to handle error response from API
def handle_api_error(response):
    if response.status_code != 200:
        raise Exception(f"Failed to retrieve data. Status code: {response.status_code}")

# Function to retrieve access token using provided credentials
def get_access_token(credentials_file):
    # Retrieve access token using provided credentials
    with open(credentials_file) as json_file:
        credentials = json.load(json_file)
    
    response = requests.post(url=AUTH_URL, data=credentials)
    handle_api_error(response)
    return json.loads(response.text)['access_token']

def get_positions(access_token):
    # Construct API URL
    url = f'{API_BASE_URL}/positions'
    headers = {"accept": "application/json"}
    params = {'access_token': access_token}

    # Get position data
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        position_data = response.json().get('data')
        positions_dict = {}
        for index, position in enumerate(position_data):
            positions_dict[index] = {
                'id': str(position.get('id')),
                'name': position.get('name'),
                'location': position['location'].get('name', 'Internal') if 'location' in position else 'Internal'
            }
        return positions_dict
    else:
        print(f"Failed to retrieve shifts. Status code: {response.status_code}")
        return None


def get_shifts(start_date, end_date, access_token, positions={}, mode='overview'):
    # Format URL parameters
    schedule = ', '.join(positions.keys())
    params = {
        'start_date': str(start_date),
        'end_date': str(end_date),
        'mode': mode,
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


def filter_include(df, positions):
    with open('./output/positions.json') as json_file:
        data = json.load(json_file)
    pos_id = [entry['id'] for entry in data.values() if entry['name'] in positions]
    return df[df['Pos_id'].isin(pos_id)]
        

if __name__ == '__main__':
    access_token = get_access_token(CREDENTIALS_FILE)
    # Get position data and save to csv if needed
    positions = get_positions(access_token)
    if isinstance(positions, dict):
        with open(POSITIONS_FILE, 'w') as json_file:
            json.dump(positions, json_file, indent=2)

    start_date = datetime.date(2023, 11, 1)
    end_date = datetime.date(2023, 11, 30)
    
    shifts_data = get_shifts(start_date, end_date, access_token)
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
        positions = '24/7 Cisco Urgent', '24/7 T1 Urgent', '24/7 T2 Planned/Backup'
        filtered_shift_report = filter_include(shift_report, positions)
        standby_report = filtered_shift_report.groupby('Name').agg(
            Number_of_shifts=('Position', 'count'),
            Total_hours=('Employee_hours', 'sum'),
            Total_weekday_hours=('Weekday_hours', 'sum'),
            Total_weekend_hours=('Weekend_hours', 'sum')
        ).reset_index()

        # Formatting the columns with floating-point numbers to two decimal places
        standby_report['Total_hours'] = standby_report['Total_hours'].round(2)
        standby_report['Total_weekday_hours'] = standby_report['Total_weekday_hours'].round(2)
        standby_report['Total_weekend_hours'] = standby_report['Total_weekend_hours'].round(2)

        print(standby_report)
        timeline = f'{start_date.strftime("%Y-%m-%d")}_{end_date.strftime("%Y-%m-%d")}'
        output_path = f'./output/report_{timeline}'
        comment = f'This report includes positions: {positions} for the time period of {timeline}'
        # Save the report to a CSV file with a comment
        with open(output_path, 'w') as f:
            f.write('# ' + comment + '\n')
            standby_report.to_csv(f, index=False)
    else:
        # Handle failed API request
        pass
