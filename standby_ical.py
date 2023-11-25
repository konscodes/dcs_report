'''
Simple version taking data from ical and exporting csv
! Does not work because it is not easy to parse description field !
! Sometimes it includes title or notes, sometimes doesn't !

1. Read ical data
2. Convert the ics data into pandas df
3. Modify the data to list
    - Name, Number of shifts, Total hours, Weekday hours, Weekend hours
    - Account for breaks
4. Export the report to csv
'''

import os
from pathlib import Path

import pandas as pd
import requests
from ics import Calendar

script_path = Path(__file__).resolve()

# Define a function to parse the description field
def parse_description(description: str | None) -> tuple[str, str]:
    if not description:
        raise TypeError('Event description is empty, unable to proceed')
    lines = description.split("\n")
    shift_name = 'NA' if lines[0].strip() == 'Working:' else lines[0].strip()
    engineer_name = lines[-1].strip()[2:]  # Strip the first two characters (dashes)
    return shift_name, engineer_name

# Define a function to calculate business hours
def calculate_business_hours(shift_name: str) -> int:
    if shift_name == "Morning/Day":
        return 9 # Business hours from 9:00 to 18:00
    else:
        return 0  # Set to None for other shifts

# Define a function to calculate Total OT
def calculate_total_ot(scheduled_hours, business_hours):
    if business_hours is not None:
        return scheduled_hours - business_hours
    else:
        return None  # Set to None for other shifts

# Define the iCal URL (DCS Schedule Overview)
ical_url = os.environ["CALENDAR_URL"]

# Fetch the iCal data from the URL
response = requests.get(ical_url)
ical_data = response.text

# Parse the iCal data
calendar = Calendar(ical_data)

# Initialize a list to store event data
event_data = []

# Iterate through the calendar events
for event in calendar.events:
    event_title = event.name
    event_date = event.begin.date()  # Extract the date of the event
    scheduled_hours = (event.end - event.begin).total_seconds() / 3600  # Calculate hours
    event_description = event.description
    shift_name, engineer_name = parse_description(event_description)
    business_hours = calculate_business_hours(shift_name)
    total_ot = calculate_total_ot(scheduled_hours, business_hours)
    event_data.append([event_date, event_title, scheduled_hours, shift_name, engineer_name, business_hours, total_ot])

# Create a DataFrame using pandas
df = pd.DataFrame(event_data, columns=["Event Date", "Event Title", "Total Scheduled Hours", "Shift Name", "Engineer Name", "Business Hours", "Total OT"])

# Sort the DataFrame by Event Date
df = df.sort_values(by="Event Date")

# Define the output CSV file name
csv_file_name = script_path.parent / 'calendar_events.csv'

# Write the DataFrame to CSV
df.to_csv(csv_file_name, index=False)

print(f"Events with descriptions, business hours, and total OT added as columns have been written to {csv_file_name}")

# Group the DataFrame by Engineer Name and sum the Total OT
engineer_totals = df.groupby("Engineer Name")["Total OT"].sum().reset_index()

# Define the grouped CSV file name
grouped_csv_file_name = script_path.parent / 'calendar_events_grouped.csv'

# Write the grouped DataFrame to CSV
engineer_totals.to_csv(grouped_csv_file_name, index=False)

print(f"Events grouped by Engineer Name with total OT added as columns have been written to {grouped_csv_file_name}")
