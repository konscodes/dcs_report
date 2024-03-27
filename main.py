import argparse
import datetime
import json
from pathlib import Path

from api_handler import get_access_token, get_positions, get_shifts
from office_handler import get_email_details, send_email
from report_generator import generate_shift_report, generate_standby_report

script_path = Path(__file__).resolve()
script_parent = script_path.parent

# Constants and configurations
CREDENTIALS_FILE = script_parent / 'auth' / 'credentials_humanity.json'
POSITIONS_FILE = script_parent / 'files' / 'positions.json'
EMAIL_FILE = script_parent / 'files' / 'email_details.json'
OUTPUT_REPORT_PATH = script_parent / 'output' / 'report_'
DEFAULT_POSITIONS = {
    '3115142': '24/7 Cisco Urgent',
    '3115140': '24/7 O1 Urgent',
    '3115141': '24/7 O2 Planned/Backup',
    '3110230': '24/7 Cisco Urgent',
    '3110228': '24/7 T1 Urgent',
    '3110229': '24/7 T2 Planned/Backup'
}


def get_date(date_str):
    try:
        return datetime.datetime.strptime(date_str, '%m.%d.%Y').date()
    except ValueError:
        raise argparse.ArgumentTypeError('Invalid date format. Use mm.dd.yyyy')


def last_month_first_day():
    today = datetime.date.today()
    last_month = today.replace(day=1) - datetime.timedelta(days=1)
    return last_month.replace(day=1)


def last_month_last_day():
    today = datetime.date.today()
    return today.replace(day=1) - datetime.timedelta(days=1)


def get_position_names(json_data, select_positions):
    position_names = []
    for entry in json_data.values():
        if entry['id'] in select_positions:
            position_names.append(entry['name'])
    return position_names


if __name__ == '__main__':
    # Get position data and save to csv if needed
    access_token = get_access_token(CREDENTIALS_FILE)
    positions = get_positions(access_token)
    if isinstance(positions, dict):
        with open(POSITIONS_FILE, 'w') as json_file:
            json.dump(positions, json_file, indent=2)

    # Manage script command line arguments
    parser = argparse.ArgumentParser(description='Process report start date')
    parser.add_argument('--report_start_date',
                        nargs='?',
                        type=get_date,
                        default=last_month_first_day(),
                        help='Report start date in mm.dd.yyyy format')
    parser.add_argument('--report_end_date',
                        nargs='?',
                        type=get_date,
                        default=last_month_last_day(),
                        help='Report end date in mm.dd.yyyy format')
    parser.add_argument('--select_positions',
                        nargs='*',
                        default=DEFAULT_POSITIONS.keys(),
                        help='List of positions (e.g. 3115142, 3115141)')
    parser.add_argument('--email_report',
                        action='store_true',
                        default=True,
                        help='Send the report over email True or False')
    args = parser.parse_args()

    report_start_date = args.report_start_date
    report_end_date = args.report_end_date
    select_positions = args.select_positions
    email_report = args.email_report

    # Fetch shift data from the API
    shifts_data = get_shifts(report_start_date, report_end_date, access_token)
    if not shifts_data:
        raise Exception('Shift data is empty')

    # Generate the report
    shift_report = generate_shift_report(shifts_data)
    standby_report = generate_standby_report(shift_report, select_positions)

    # Export the report to csv
    timeline = f'{report_start_date.strftime("%Y-%m-%d")}_{report_end_date.strftime("%Y-%m-%d")}'
    report_name = f'report_{timeline}.csv'
    report_path = script_parent / 'output' / report_name
    position_names = get_position_names(positions, select_positions)
    comment = f'This report includes positions: {"; ".join(position_names)} for the time period of {timeline.replace("_", " to ")}'
    print(comment, '\n', standby_report)

    with open(report_path, 'w') as f:
        f.write('# ' + comment + '\n')
        standby_report.to_csv(f, index=False)

    # Send the report over email
    if email_report:
        print('Sending email..')

        # Set email details
        sender_email, recipient_emails, subject_default, body_default = get_email_details(
            EMAIL_FILE)
        subject = f'Shift report - {report_start_date.strftime("%b %Y")}'
        body = f'Included positions: {"; ".join(position_names)}\n' + f'Time period: {timeline.replace("_", " to ")}\n\n' + body_default
        send_email(sender_email,
                   recipient_emails,
                   subject,
                   body,
                   attachment_path=report_path)

    # Timesheet report
    # TODO
    # Add shift notes to the shift report (or replace shift report with different data that includes notes)
    # Similar to positions fetch employee list with ids and emails
    # Create new timesheet report df
    # For each employee in a shift report
    #     - Include Date, Position, Start time, End time, Overtime, Shift Title, Notes
    #     - Group and sort by date
    #     - Save the output to csv
    #     - Save the output to csv
    # For each employee in a shift report
    #     - Include Date, Position, Start time, End time, Overtime, Shift Title, Notes
    #     - Group and sort by date
    #     - Save the output to csv
    #     - Save the output to csv
