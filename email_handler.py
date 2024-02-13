import json
import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def read_json(filename):
    with open(filename, 'r') as file:
        data = json.load(file)
    return data


def get_email_credentials(filename):
    credentials = read_json(filename)
    smtp_server = credentials['smtp_server']
    smtp_port = credentials['smtp_port']
    email_address = credentials['email_address']
    email_password = credentials['email_password']
    return smtp_server, smtp_port, email_address, email_password


def get_recipient_emails(filename):
    recipient_data = read_json(filename)
    to_emails = recipient_data['recipients']
    return to_emails


def create_email(subject, message, from_email, to_emails, attachment_filename):
    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = ', '.join(to_emails)
    msg['Subject'] = subject

    msg.attach(MIMEText(message, 'plain'))

    with open(attachment_filename, 'rb') as attachment:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachment.read())

    encoders.encode_base64(part)
    part.add_header(
        "Content-Disposition",
        f"attachment; filename= {attachment_filename}",
    )

    msg.attach(part)

    return msg


def send_email(smtp_server, smtp_port, email_address, email_password, msg):
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(email_address, email_password)
        text = msg.as_string()
        server.sendmail(msg['From'], msg['To'].split(', '), text)


if __name__ == '__main__':
    # Usage example
    smtp_server, smtp_port, email_address, email_password = get_email_credentials(
        'credentials_smtp.json')
    to_emails = get_recipient_emails('recipients.json')

    subject = 'CSV file'
    message = 'Please find the attached CSV file.'
    from_email = email_address
    attachment_filename = './output/report_2024-02-01_2024-02-28.csv'

    email_msg = create_email(subject, message, from_email, to_emails,
                             attachment_filename)
    send_email(smtp_server, smtp_port, email_address, email_password,
               email_msg)
