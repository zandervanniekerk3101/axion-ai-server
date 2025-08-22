import os
import json
import logging
from flask import Flask, request, jsonify, Response, url_for
from twilio.rest import Client as TwilioClient
from twilio.twiml.voice_response import VoiceResponse, Gather
from dotenv import load_dotenv
import openai
from collections import defaultdict

# ---------- Setup ----------
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("axiom")

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN  = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_NUMBER      = os.getenv("TWILIO_NUMBER")          # E.164, e.g. +12025550123
PUBLIC_BASE_URL    = os.getenv("PUBLIC_BASE_URL")        # e.g. https://axiom-ai-server.onrender.com

OPENAI_API_KEY     = os.getenv("OPENAI_API_KEY")
openai.api_key     = OPENAI_API_KEY

twilio = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# In-memory convo state (prod: redis)
SESSION = defaultdict(lambda: {"history": []})

app = Flask(__name__)

# ---------- Helpers ----------
def ai_reply(call_sid, user_text):
    """Turn-by-turn: keep short, call-safe replies."""
    state = SESSION[call_sid]
    state["history"].append({"role": "user", "content": user_text})

    # Keep it snappy & phone-friendly
    system = "You are Axiom AI, a phone assistant. Be concise, speak plainly, avoid long sentences."
    messages = [{"role": "system", "content": system}] + state["history"]

    try:
        resp = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages
        )
        text = resp.choices[0].message.content.strip()
    except Exception as e:
        logger.exception("OpenAI error")
        text = "Sorry, I hit a brain freeze. Say that again?"

    state["history"].append({"role": "assistant", "content": text})
    return text

def absolute(url_path):
    # Build absolute URL for Twilio callbacks
    if url_path.startswith("http"):
        return url_path
    return f"{PUBLIC_BASE_URL}{url_path}"

# ---------- Root ----------
@app.route("/")
def home():
    return "Axiom AI Server is Online!"

# =========================================================
# INBOUND CALL: Conversational loop using <Gather> (speech)
# =========================================================
@app.route("/incoming_call", methods=["POST"])
def incoming_call():
    call_sid = request.form.get("CallSid")
    from_num = request.form.get("From")

    # Seed the conversation
    greeting = "Hey, this is Axiom. How can I help you right now?"
    SESSION[call_sid]["history"] = [{"role": "assistant", "content": greeting}]

    vr = VoiceResponse()
    vr.say(greeting, voice="alice")

    # Gather caller speech, then POST to /process_speech
    gather = Gather(
        input="speech",
        speechTimeout="auto",
        action="/process_speech",
        method="POST",
        language="en-ZA"  # tweak if needed
    )
    vr.append(gather)
    # If no speech, reprompt
    vr.redirect("/reprompt")
    return Response(str(vr), mimetype="text/xml")

@app.route("/reprompt", methods=["POST"])
def reprompt():
    vr = VoiceResponse()
    vr.say("I didn’t catch that. What do you need?", voice="alice")
    gather = Gather(
        input="speech",
        speechTimeout="auto",
        action="/process_speech",
        method="POST",
        language="en-ZA"
    )
    vr.append(gather)
    vr.redirect("/reprompt")
    return Response(str(vr), mimetype="text/xml")

@app.route("/process_speech", methods=["POST"])
def process_speech():
    call_sid = request.form.get("CallSid")
    speech = request.form.get("SpeechResult", "") or ""
    logger.info(f"[{call_sid}] Caller said: {speech}")

    # Turn-by-turn with GPT
    reply = ai_reply(call_sid, speech)

    # Speak reply, then keep gathering
    vr = VoiceResponse()
    vr.say(reply, voice="alice")
    gather = Gather(
        input="speech",
        speechTimeout="auto",
        action="/process_speech",
        method="POST",
        language="en-ZA"
    )
    vr.append(gather)
    return Response(str(vr), mimetype="text/xml")

# =========================================================
# OUTBOUND: Deliver a message to someone (your instruction)
# =========================================================
@app.route("/call_deliver_message", methods=["POST"])
def call_deliver_message():
    """
    JSON body: { "to": "+27...", "message": "Your message text" }
    Axiom calls the person and reads the message. Records the call.
    """
    data = request.get_json(force=True)
    to = data["to"]
    message = data["message"]

    tw = twilio.calls.create(
        to=to,
        from_=TWILIO_NUMBER,
        url=absolute(f"/twi_deliver?msg={json.dumps(message)}"),
        record="record-from-answer-dual",
        status_callback=absolute("/status_callback"),
        status_callback_event=["initiated", "ringing", "answered", "completed"]
    )
    return jsonify({"call_sid": tw.sid})

@app.route("/twi_deliver", methods=["POST", "GET"])
def twi_deliver():
    # message passed as query param (URL-safe via json dumps)
    msg = request.args.get("msg", "\"Hi.\"")
    try:
        text = json.loads(msg)
    except Exception:
        text = "Hello, this is Axiom calling with a message."

    vr = VoiceResponse()
    vr.say(text, voice="alice")
    # Optionally allow a short reply from callee:
    gather = Gather(input="speech", speechTimeout="auto", action="/twi_deliver_capture", method="POST")
    gather.say("If you want to leave a quick response, say it after the beep.", voice="alice")
    vr.append(gather)
    vr.say("Okay, goodbye.", voice="alice")
    return Response(str(vr), mimetype="text/xml")

@app.route("/twi_deliver_capture", methods=["POST"])
def twi_deliver_capture():
    speech = request.form.get("SpeechResult", "")
    logger.info(f"Deliver call response: {speech}")
    vr = VoiceResponse()
    vr.say("Thanks, noted. Bye.", voice="alice")
    return Response(str(vr), mimetype="text/xml")

# =========================================================
# WORKFLOW: Proposal call -> then auto-call you back with summary
# =========================================================
@app.route("/call_business_proposal", methods=["POST"])
def call_business_proposal():
    """
    Body:
    {
      "business_number": "+27...",
      "script": "Hi, I'm calling with a proposal ...",
      "your_number": "+27..."   # Axiom will call you after to summarize
    }
    """
    data = request.get_json(force=True)
    business_number = data["business_number"]
    script = data["script"]
    your_number = data["your_number"]

    # 1) Call business with script, record & transcribe
    tw = twilio.calls.create(
        to=business_number,
        from_=TWILIO_NUMBER,
        url=absolute(f"/twi_deliver?msg={json.dumps(script)}"),
        record="record-from-answer-dual",
        transcribe=True,
        transcribe_callback=absolute("/transcription_ready"),
        status_callback=absolute("/status_callback"),
        status_callback_event=["completed"],
    )

    # Stash who to call back when done
    app.config[f"CALLBACK_{tw.sid}"] = your_number
    return jsonify({"proposal_call_sid": tw.sid})

@app.route("/transcription_ready", methods=["POST"])
def transcription_ready():
    # Twilio sends transcription text for a recording
    transcript_text = request.form.get("TranscriptionText", "")
    recording_url   = request.form.get("RecordingUrl", "")
    call_sid        = request.form.get("CallSid", "")

    logger.info(f"[TRANSCRIPT] {call_sid}: {transcript_text}")
    logger.info(f"[RECORDING] {call_sid}: {recording_url}")

    # Summarize via GPT for the callback to user
    prompt = f"Summarize this phone call in 5 bullet points with any follow-ups:\n\n{transcript_text}"
    try:
        resp = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a concise call summarizer."},
                {"role": "user", "content": prompt}
            ]
        )
        summary = resp.choices[0].message.content.strip()
    except Exception:
        logger.exception("OpenAI summarization failed")
        summary = "Call completed. Transcript not available."

    # Save summary somewhere durable (stub)
    save_summary_to_sheets(call_sid, summary, recording_url)

    # Store for call-back
    app.config[f"SUMMARY_{call_sid}"] = summary
    return ("", 204)

@app.route("/status_callback", methods=["POST"])
def status_callback():
    call_sid = request.form.get("CallSid")
    call_status = request.form.get("CallStatus")
    logger.info(f"[STATUS] {call_sid}: {call_status}")

    # When proposal call completes, ring you back with the summary
    if call_status == "completed":
        your_number = app.config.get(f"CALLBACK_{call_sid}")
        summary = app.config.get(f"SUMMARY_{call_sid}", "The call is complete.")
        if your_number:
            # Place a new call to you with the summary
            twilio.calls.create(
                to=your_number,
                from_=TWILIO_NUMBER,
                url=absolute(f"/twi_read_summary?sid={call_sid}")
            )
    return ("", 204)

@app.route("/twi_read_summary", methods=["POST", "GET"])
def twi_read_summary():
    call_sid = request.args.get("sid")
    summary = app.config.get(f"SUMMARY_{call_sid}", "No summary found.")
    vr = VoiceResponse()
    vr.say("Axiom here. Here’s the result of the last call.", voice="alice")
    vr.say(summary, voice="alice")
    vr.say("Want me to take any next actions?", voice="alice")

    # Let you answer, route back into a small gather flow
    gather = Gather(input="speech", speechTimeout="auto", action="/process_owner_instruction", method="POST")
    vr.append(gather)
    vr.say("If you need anything else, just call me back. Bye.", voice="alice")
    return Response(str(vr), mimetype="text/xml")

@app.route("/process_owner_instruction", methods=["POST"])
def process_owner_instruction():
    speech = request.form.get("SpeechResult", "")
    logger.info(f"[OWNER INSTRUCTION] {speech}")

    # TODO: parse intents like "call supplier", "get a price", "book at 3pm", etc.
    # For now, just confirm.
    vr = VoiceResponse()
    vr.say("Got it. I’ll handle that next.", voice="alice")
    return Response(str(vr), mimetype="text/xml")

# =========================================================
# Basic “ask” endpoint for your app
# =========================================================
@app.route("/ask", methods=["POST"])
def ask_axiom():
    data = request.get_json(force=True)
    user_prompt = data.get("prompt", "")
    try:
        completion = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are Axiom AI, a helpful business assistant."},
                {"role": "user", "content": user_prompt}
            ]
        )
        ai_response = completion.choices[0].message.content
        return jsonify({"response": ai_response})
    except Exception as e:
        logger.exception("OpenAI chat failed")
        return jsonify({"error": "AI error"}), 500

# =========================================================
# Google Sheets/Docs stubs (you’ll wire creds)
# =========================================================
def save_summary_to_sheets(call_sid, summary, recording_url):
    """
    TODO: Implement Google API writes here.
    Example columns: timestamp, call_sid, summary, recording_url
    """
    logger.info(f"[SHEETS-STUB] Save {call_sid} | {len(summary)} chars | {recording_url}")
    # Real impl: use gspread / google-api-python-client with a service account.

# ---------- Main ----------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=True)