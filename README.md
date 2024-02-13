# DCS Report
Fetch the shift data from Humanity API to create custom reports
1. Create pandas df for shifts (Name, Position, Pos_id, Title, Start date, End date, Employee_hours, Shift_hours)
2. Request the overview of shift data from Humanity API
    - auth with API using credentials and token
    - specify period (start date to end date)
    - optionally request a position data from API to save store locally as a json
3. Parse the response data and insert items into pandas df for shifts
- Each data point has employees
- For each employee in this data point add and entry into df and include
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