import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, To, From
from dotenv import load_dotenv

load_dotenv()

SENDGRID_API_KEY = os.getenv("SENDGRID_KEY")
EMAIL_FROM = From("blogueandoando.blog@gmail.com", "BlogueandoAndo")

TEMPLATE_CONFIRMATION_ID = "d-ac182bd1ef374686b3d21ad210fbf1f3"
TEMPLATE_RESET_PASSWORD_ID = "d-730e0283f83344b8aa4a1dac92844c36"

def send_email(to_email, template_id, dynamic_data):
    message = Mail(
        from_email=EMAIL_FROM,
        to_emails=To(to_email)
    )

    message.dynamic_template_data = dynamic_data
    message.template_id = template_id

    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        print(f"Email sent! Status Code: {response.status_code}")
    except Exception as e:
        print(f"Error sending email: {e}")

def send_confirmation_email(to_email, user_name, verification_link):
    send_email(to_email, TEMPLATE_CONFIRMATION_ID, {
        "user_name": user_name,
        "verification_link": verification_link
    })

def send_password_reset_email(to_email, user_name, reset_link):
    send_email(to_email, TEMPLATE_RESET_PASSWORD_ID, {
        "user_name": user_name,
        "reset_link": reset_link
    })