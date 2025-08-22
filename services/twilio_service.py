import os
from twilio.rest import Client
from flask import url_for

# --- Load Environment Variables ---
account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
twilio_phone_number = os.environ.get("TWILIO_PHONE_NUMBER")
server_url = os.environ.get("SERVER_URL")  # e.g., https://yourapp.loca.lt

# --- Fail Fast if Config Missing ---
if not all([account_sid, auth_token, twilio_phone_number, server_url]):
    raise Exception("Twilio environment variables are not fully configured!")

# --- Twilio Client ---
client = Client(account_sid, auth_token)


def make_phone_call(to_number: str, message: str):
    """
    Simple one-way call: speaks a message to the recipient.
    """
    try:
        twiml = f'<Response><Say voice="Polly.Joanna">{message}</Say></Response>'
        call = client.calls.create(
            twiml=twiml,
            to=to_number,
            from_=twilio_phone_number
        )
        return {"status": "success", "sid": call.sid}
    except Exception as e:
        print(f"!!! TWILIO CALL ERROR: {str(e)}")
        return {"status": "error", "error": str(e)}


def make_interactive_call(to_number: str, endpoint: str = "/twilio/voice"):
    """
    Starts a call that fetches TwiML from a webhook endpoint (Flask/FastAPI route).
    This allows full AI-driven conversations instead of static messages.
    """
    try:
        twiml_url = f"{server_url}{endpoint}"
        call = client.calls.create(
            url=twiml_url,
            to=to_number,
            from_=twilio_phone_number,
            record=True  # record the call for summarization
        )
        return {"status": "success", "sid": call.sid, "twiml_url": twiml_url}
    except Exception as e:
        print(f"!!! TWILIO INTERACTIVE CALL ERROR: {str(e)}")
        return {"status": "error", "error": str(e)}


def get_call_details(call_sid: str):
    """
    Fetches details about a call (status, duration, recordings, etc.)
    """
    try:
        call = client.calls(call_sid).fetch()
        return {
            "sid": call.sid,
            "status": call.status,
            "to": call.to,
            "from": call.from_,
            "start_time": str(call.start_time),
            "end_time": str(call.end_time),
            "duration": call.duration
        }
    except Exception as e:
        print(f"!!! TWILIO FETCH ERROR: {str(e)}")
        return {"status": "error", "error": str(e)}


def get_recordings(call_sid: str):
    """
    Fetch recordings for a call (if recording was enabled).
    """
    try:
        recordings = client.recordings.list(call_sid=call_sid)
        return [{"sid": r.sid, "url": f"https://api.twilio.com{r.uri}"} for r in recordings]
    except Exception as e:
        print(f"!!! TWILIO RECORDING ERROR: {str(e)}")
        return {"status": "error", "error": str(e)}