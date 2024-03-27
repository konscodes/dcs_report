import base64
import json
from pathlib import Path

import requests

script_path = Path(__file__).resolve()
script_parent = script_path.parent

# Constants and configurations
OFFICE_CREDENTIALS_FILE = script_parent / 'auth' / 'credentials_office.json'


def read_json(filename):
    with open(filename, 'r') as file:
        data = json.load(file)
    return data


def get_office_credentials(filename):
    credentials = read_json(filename)
    tenant_id = credentials['tenant_id']
    client_id = credentials['client_id']
    client_secret = credentials['client_secret']
    return tenant_id, client_id, client_secret


def get_email_details(filename):
    email = read_json(filename)
    sender_email = email['sender_email']
    recipient_emails = email['recipient_emails']
    subject = email['subject']
    body = email['body']
    return sender_email, recipient_emails, subject, body


def get_access_token(tenant_id, client_id, client_secret):
    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    data = {
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret,
        'scope': 'https://graph.microsoft.com/.default'
    }
    response = requests.post(token_url, data=data)
    if response.status_code == 200:
        return response.json()['access_token']
    else:
        print(f"Failed to obtain access token: {response.text}")
        return None


def send_email(sender_email,
               recipient_emails,
               subject,
               body,
               attachment_path=None):
    # Get credentials from JSON files
    tenant_id, client_id, client_secret = get_office_credentials(
        OFFICE_CREDENTIALS_FILE)

    # Obtain access token internally
    access_token = get_access_token(tenant_id, client_id, client_secret)

    url = "https://graph.microsoft.com/v1.0/users/" + sender_email + "/sendMail"
    if access_token:
        headers = {
            "Authorization": "Bearer " + access_token,
            "Content-Type": "application/json"
        }
    else:
        print("Failed to obtain access token")
        return None

    # Create recipients list
    to_recipients = []
    for recipient_email in recipient_emails:
        to_recipients.append({"emailAddress": {"address": recipient_email}})

    # Prepare attachment
    attachments = []
    if attachment_path:
        with open(attachment_path, 'rb') as file:
            content = base64.b64encode(file.read()).decode('utf-8')
            attachments.append({
                "@odata.type": "#microsoft.graph.fileAttachment",
                "name": attachment_path.name,
                "contentBytes": content
            })

    # Prepare payload
    payload = {
        "message": {
            "subject": subject,
            "body": {
                "contentType": "Text",
                "content": body
            },
            "toRecipients": to_recipients
        }
    }

    # Add attachments if available
    if attachments:
        payload['message']['attachments'] = attachments

    # Send email
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 202:
        print("Email sent successfully!")
    else:
        print(f"Failed to send email: {response.text}")


if __name__ == '__main__':
    # Set email details
    sender_email, recipient_emails, subject, body = get_email_details(
        './files/email_details.json')
    attachment_path = "./output/report_2024-01-01_2024-01-31.csv"  # Path to the attachment file

    # Send email
    send_email(sender_email, recipient_emails, subject, body, attachment_path)
