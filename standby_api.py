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
def handle_api_error(response: requests.Response) -> None:
    if response.status_code != 200:
        raise Exception(f"Failed to retrieve data. Status code: {response.status_code}")

# Function to retrieve access token using provided credentials
def get_access_token(credentials_file: str) -> str:
    # Retrieve access token using provided credentials
    with open(credentials_file) as json_file:
        credentials = json.load(json_file)
    
    response = requests.post(url=AUTH_URL, data=credentials)
    handle_api_error(response)
    return json.loads(response.text).get('access_token')

def get_positions(access_token: str) -> dict | None:
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


def get_shifts(start_date: datetime.date, end_date: datetime.date, access_token: str, positions: dict = {}, mode: str = 'overview') -> dict | None:
    # Construct API URL
    url = f'{API_BASE_URL}/shifts'
    headers = {"accept": "application/json"}

    # Format URL parameters
    params = {
        'start_date': str(start_date),
        'end_date': str(end_date),
        'mode': mode,
        'access_token': access_token
    }
    if positions:
        params['schedule'] = ', '.join(positions.keys())

    # Get shift data
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to retrieve shifts. Status code: {response.status_code}")
        return None


def parse_data(shifts_data: dict) -> pd.DataFrame:
    '''Parse shift data into pandas DataFrame

    Args:
        shifts_data (dict): Shift data dict received from API

    Returns:
        pd.DataFrame: Shifts DataFrame
    '''
    data_list = []
    for shift in shifts_data['data']:
        shift_id = shift['id']
        shift_start = shift['start_timestamp']
        shift_end = shift['end_timestamp']
        shift_position = shift['schedule_name']
        shift_pos_id = shift['schedule']
        shift_title = shift['title']
        shift_hours = shift['paidtime']

        def add_data(employee_name, employee_hours):
            data_list.append({
                'Shift_id': shift_id,
                'Name': employee_name,
                'Position': shift_position,
                'Pos_id': shift_pos_id,
                'Title': shift_title,
                'Start_date': shift_start,
                'End_date': shift_end,
                'Employee_hours': employee_hours,
                'Shift_hours': shift_hours,
            })

        # Check if 'employees' key exists and is a list
        if 'employees' in shift and isinstance(shift['employees'], list):
            for employee in shift['employees']:
                add_data(employee['name'], employee['paidtime'])

        # Account for OnCall shifts
        if 'employeesOnCall' in shift and isinstance(shift['employeesOnCall'], list):
            for employee in shift['employeesOnCall']:
                add_data(employee['name'], shift_hours)

    return pd.DataFrame(data_list)


def calculate_overtime(shift_start: pd.Timestamp, shift_end: pd.Timestamp) -> float:
    '''Assuming only weekdays, return total overtime outside of business hours

    Args:
        shift_start (pd.Timestamp): Start of the shift
        shift_end (pd.Timestamp): End of the shift

    Returns:
        float: Total overtime
    '''
    bau_start = shift_start.replace(hour=9, minute=0, second=0)
    bau_end = shift_start.replace(hour=18, minute=0, second=0)
    
    # If the start time is after the bau end or end time is before the bau start
    if shift_start >= bau_end or shift_end <= bau_start:
        return (shift_end - shift_start).total_seconds() / 3600  # Total hours outside the bau
    
    # Calculating the duration outside the bau
    before_bau = max(0, (bau_start - shift_start).total_seconds() / 3600)
    after_bau = max(0, (shift_end - bau_end).total_seconds() / 3600)
    
    overtime = before_bau + after_bau
    return overtime


def separate_hours(shift_start_dates: pd.Series, shift_end_dates: pd.Series) -> tuple:
    '''Analyze given start and end Series and return a breakdown into weekend, weekday and overtime for each pair

    Args:
        shift_start_dates (pd.Series): Series of start dates for each shift
        shift_end_dates (pd.Series): Series of end dates for each shift

    Returns:
        tuple (list[float], list[float], list[float]): weekday_hours, weekend_hours, overtime
    '''
    weekday_hours: list[float] = []
    weekend_hours: list[float] = []
    overtime: list[float] = []

    # Ensure shift_start_dates and end_date are Pandas Series of Timestamps
    shift_start_dates = pd.to_datetime(shift_start_dates)
    shift_end_dates = pd.to_datetime(shift_end_dates)

    for i in range(len(shift_start_dates)):
        shift_start: pd.Timestamp = shift_start_dates.iloc[i]
        shift_end: pd.Timestamp = shift_end_dates.iloc[i]
        
        # Shift starts and ends within weekdays
        if shift_start.weekday() < 5 and shift_end.weekday() < 5:
            weekday_hours.append((shift_end - shift_start).total_seconds() / 3600)
            weekend_hours.append(0)
            # Log overtime for hours outside of business start (9am) to business end (6pm)
            overtime.append(calculate_overtime(shift_start, shift_end))
        
        # Shift starts and ends within weekends
        elif shift_start.weekday() >= 5 and shift_end.weekday() >= 5:
            weekend_hours.append((shift_end - shift_start).total_seconds() / 3600)
            weekday_hours.append(0)
            # Log all weekend time towards overtime
            overtime.append((shift_end - shift_start).total_seconds() / 3600)
        
        # Shift spans across weekend and weekdays
        else:
            midnight = shift_end.replace(hour=0, minute=0, second=0)
            after_midnight = (shift_end - midnight).total_seconds() / 3600
            before_midnight = (midnight - shift_start).total_seconds() / 3600
            # Shift starts on weekday and ends on weekend
            if shift_start.weekday() < 5:
                weekday_hours.append(before_midnight)
                weekend_hours.append(after_midnight)
                # Log overtime for hours outside of business start (9am) to business end (6pm) starting from start date up till midnight
                # Log all weekend time towards overtime
                overtime.append(calculate_overtime(shift_start, midnight) + after_midnight)
            
            # Shift starts on weekend and ends on weekday
            else:
                weekday_hours.append(after_midnight)
                weekend_hours.append(before_midnight)         
                # Log all weekend time towards overtime
                # Log overtime for hours outside of business start (9am) to business end (6pm) starting from midnight till the end date
                overtime.append(before_midnight + calculate_overtime(midnight, shift_end))
    return weekday_hours, weekend_hours, overtime


def filter_include(df: pd.DataFrame, positions: tuple) -> pd.DataFrame:
    '''Return filtered Series where position includes given position names

    Args:
        df (pd.DataFrame): Shifts DataFrame to be filtered 
        positions (tuple): List of position names to match against

    Returns:
        pd.DataFrame: Filtered Series
    '''
    with open('./output/positions.json') as json_file:
        data = json.load(json_file)
    pos_id = [entry['id'] for entry in data.values() if entry['name'] in positions]
    
    filtered_df = df[df['Pos_id'].isin(pos_id)]
    return pd.DataFrame(filtered_df)
        

if __name__ == '__main__':
    access_token = get_access_token(CREDENTIALS_FILE)
    # Get position data and save to csv if needed
    positions = get_positions(access_token)
    if isinstance(positions, dict):
        with open(POSITIONS_FILE, 'w') as json_file:
            json.dump(positions, json_file, indent=2)

    report_start_date = datetime.date(2022, 2, 1)
    report_end_date = datetime.date(2022, 2, 28)
    
    shifts_data = get_shifts(report_start_date, report_end_date, access_token)
    if shifts_data:
        # Process shifts_data as needed
        shift_report = parse_data(shifts_data)
        
        # Calculate weekday and weekend hours for each shift
        start_dates = shift_report.loc[:, 'Start_date']
        end_dates = shift_report.loc[:, 'End_date']

        weekday_hours, weekend_hours, overtime = separate_hours(
            start_dates, end_dates
        )

        # Add additional columns to shift_report
        shift_report['Break'] = shift_report['Shift_hours'] - shift_report['Employee_hours']
        # Account for missing breaks
        condition = (shift_report['Pos_id'].isin(['3110228', '3115140'])) & (shift_report['Title'] == 'Morning/Day') & (shift_report['Break'] == 0)
        shift_report.loc[condition, 'Employee_hours'] -= 9.0
        shift_report.loc[condition, 'Break'] = 9.0
        
        shift_report['Weekday_hours'] = weekday_hours - shift_report['Break']
        shift_report['Weekend_hours'] = weekend_hours
        shift_report['Overtime'] = overtime
        print(shift_report)

        ## Standby report ##
        # Grouping by 'Name' and aggregating shift count, total hours, weekday hours, and weekend hours
        positions = '24/7 T1 Urgent', '24/7 O1 Urgent', '24/7 Cisco Urgent', '24/7 O2 Planned/Backup', '24/7 T2 Planned/Backup'
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
        timeline = f'{report_start_date.strftime("%Y-%m-%d")}_{report_end_date.strftime("%Y-%m-%d")}'
        output_path = f'./output/report_{timeline}.csv'
        comment = f'This report includes positions: {"; ".join(positions)} for the time period of {timeline}'
        # Save the report to a CSV file with a comment
        with open(output_path, 'w') as f:
            f.write('# ' + comment + '\n')
            standby_report.to_csv(f, index=False)

        ## Timesheet report ##
        # TODO 
        # Add shift notes to the shift report (or replace shift report with different data that includes notes)
        # Similar to positions fetch employee list with ids and emails
        # Create new timesheet report df
        # For each employee in a shift report
        #     - Include Date, Position, Start time, End time, Overtime, Shift Title, Notes
        #     - Group and sort by date
        #     - Save the output to csv
        
