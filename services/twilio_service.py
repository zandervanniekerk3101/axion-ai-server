import os
from twilio.rest import Client

# Get your credentials from the environment variables on Render
account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
twilio_phone_number = os.environ.get("TWILIO_PHONE_NUMBER")

# Initialize the Twilio client
client = Client(account_sid, auth_token)

def make_phone_call(to_number, message):
    """
    Makes an outbound call to a specified number and speaks a message.
    """
    if not all([account_sid, auth_token, twilio_phone_number]):
        return "Twilio credentials are not configured on the server."

    try:
        # --- THIS IS THE UPGRADED PART ---
        # We now specify a premium, more human-like voice (Polly.Joanna).
        twiml_instruction = f'<Response><Say voice="Polly.Joanna">{message}</Say></Response>'

        call = client.calls.create(
            twiml=twiml_instruction,
            to=to_number,
            from_=twilio_phone_number
        )
        # Return the Call SID (a unique ID for the call)
        return f"Call initiated successfully. SID: {call.sid}"
    except Exception as e:
        # Return any error message from Twilio
        return f"Error making call: {str(e)}"