import argparse
import datetime
import json

from api_handler import get_access_token, get_positions, get_shifts
from email_handler import (create_email, get_email_credentials,
                           get_recipient_emails, send_email)
from report_generator import generate_shift_report, generate_standby_report

# Constants and configurations
CREDENTIALS_FILE = './auth/credentials.json'
CREDENTIALS_SMTP = './auth/credentials_smtp.json'
RECIPIENTS_FILE = './files/recipients.json'
POSITIONS_FILE = './files/positions.json'
OUTPUT_REPORT_PATH = './output/report_'
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


if __name__ == '__main__':
    # Get position data and save to csv if needed
    access_token = get_access_token(CREDENTIALS_FILE)
    positions = get_positions(access_token)
    if isinstance(positions, dict):
        with open(POSITIONS_FILE, 'w') as json_file:
            json.dump(positions, json_file, indent=2)

    # Manage script command line arguments
    parser = argparse.ArgumentParser(description='Process report start date')
    parser.add_argument('report_start_date',
                        nargs='?',
                        type=get_date,
                        default=last_month_first_day(),
                        help='Report start date in mm.dd.yyyy format')
    parser.add_argument('report_end_date',
                        nargs='?',
                        type=get_date,
                        default=last_month_last_day(),
                        help='Report end date in mm.dd.yyyy format')
    parser.add_argument('select_positions',
                        nargs='*',
                        default=DEFAULT_POSITIONS.keys(),
                        help='List of positions (e.g. 3115142, 3115141)')
    args = parser.parse_args()

    report_start_date = args.report_start_date
    report_end_date = args.report_end_date
    select_positions = args.select_positions

    # Fetch shift data from the API
    shifts_data = get_shifts(report_start_date, report_end_date, access_token)
    if shifts_data:
        # Generate the report
        shift_report = generate_shift_report(shifts_data)
        standby_report = generate_standby_report(shift_report, select_positions)

        # Export the report to csv
        timeline = f'{report_start_date.strftime('%Y-%m-%d')}_{report_end_date.strftime('%Y-%m-%d')}'
        report_file = f'./output/report_{timeline}.csv'
        comment = f'This report includes positions: {'; '.join(select_positions)} for the time period of {timeline}'
        print(comment,'\n', standby_report)
        
        with open(report_file, 'w') as f:
            f.write('# ' + comment + '\n')
            standby_report.to_csv(f, index=False)

        # Send the report over email
        smtp_server, smtp_port, from_email, email_password = get_email_credentials(CREDENTIALS_SMTP)
        to_emails = get_recipient_emails(RECIPIENTS_FILE)

        subject = 'CSV file'
        message = 'Please find the attached CSV file.'

        email_msg = create_email(subject, message, from_email, to_emails,
                                report_file)
        send_email(smtp_server, smtp_port, from_email, email_password,
                email_msg)

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
