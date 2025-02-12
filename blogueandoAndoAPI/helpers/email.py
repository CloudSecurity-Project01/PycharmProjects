import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, To, From
from dotenv import load_dotenv

load_dotenv()

SENDGRID_API_KEY = os.getenv("SENDGRID_KEY")
TEMPLATE_ID = "d-ac182bd1ef374686b3d21ad210fbf1f3"

def send_confirmation_email(to_email, user_name, verification_link):
    message = Mail(
        from_email=From("blogueandoando.blog@gmail.com", "BlogueandoAndo"),
        to_emails=To(to_email)
    )

    message.dynamic_template_data = {
        "user_name": user_name,
        "verification_link": verification_link
    }

    message.template_id = TEMPLATE_ID

    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        print(f"Email sent! Status Code: {response.status_code}")
    except Exception as e:
        print(f"Error sending email: {e}")