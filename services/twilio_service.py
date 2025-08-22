import os
from twilio.rest import Client

# Get your credentials from the environment variables on Render
account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
twilio_phone_number = os.environ.get("TWILIO_PHONE_NUMBER")

# Check if the credentials are all present
if not all([account_sid, auth_token, twilio_phone_number]):
    # This is a critical error, so we raise an exception to stop the server from starting incorrectly.
    raise Exception("Twilio environment variables are not fully configured!")

# Initialize the Twilio client
client = Client(account_sid, auth_token)

def make_phone_call(to_number, message):
    """
    Makes an outbound call to a specified number and speaks a message.
    """
    try:
        twiml_instruction = f'<Response><Say voice="Polly.Joanna">{message}</Say></Response>'
        call = client.calls.create(
            twiml=twiml_instruction,
            to=to_number,
            from_=twilio_phone_number
        )
        return f"Call initiated successfully. SID: {call.sid}"
    except Exception as e:
        # Log the full error to the console for debugging
        print(f"!!! TWILIO CALL ERROR: {str(e)}")
        return f"Error making call: {str(e)}"