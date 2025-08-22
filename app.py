# app.py
# This is the complete code for your Axiom AI server with all features.

import os
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import openai

# --- Imports for Twilio ---
from services.twilio_service import make_phone_call
from twilio.twiml.voice_response import VoiceResponse # NEW TwiML import

# Load the environment variables
load_dotenv()

# Set up the OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

# Create an instance of the Flask application
app = Flask(__name__)

# This is the original route to check if the server is online.
@app.route('/')
def home():
    return "Axiom AI Server is online!"

# This is the route that handles AI requests from your Android app.
@app.route('/ask', methods=['POST'])
def ask_axiom():
    # (Your existing ask_axiom code is here, no changes needed)
    data = request.get_json()
    if not data or 'prompt' not in data:
        return jsonify({"error": "Invalid request. A 'prompt' is required."}), 400

    user_prompt = data['prompt']

    try:
        completion = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are Axiom AI, a helpful and concise personal assistant."},
                {"role": "user", "content": user_prompt}
            ]
        )
        ai_response = completion.choices[0].message.content
        return jsonify({"response": ai_response})

    except Exception as e:
        print(f"Error communicating with OpenAI: {e}")
        return jsonify({"error": "Sorry, I'm having trouble connecting to my brain right now."}), 500

# This is the endpoint for making outbound calls.
@app.route('/make_call', methods=['POST'])
def handle_make_call():
    # (Your existing handle_make_call code is here, no changes needed)
    data = request.json
    if not data or 'to_number' not in data or 'message' not in data:
        return jsonify({"error": "Invalid request. 'to_number' and 'message' are required."}), 400

    to_number = data['to_number']
    message = data['message']
    result = make_phone_call(to_number, message)
    return jsonify({"status": result})

# --- NEW ENDPOINT FOR RECEIVING CALLS ---
@app.route('/incoming_call', methods=['POST'])
def handle_incoming_call():
    """
    This endpoint is called by Twilio when someone calls your number.
    It responds with TwiML instructions.
    """
    # Create a new TwiML response object
    response = VoiceResponse()

    # Add an instruction to speak a message to the caller
    response.say('Hello, you have reached Axiom AI. Please leave a message after the beep.', voice='Polly.Joanna')

    # Add an instruction to record the caller's message
    # Twilio will call the 'action' URL when the recording is finished
    response.record(action='/handle_recording', method='POST', maxLength=20, finishOnKey='*')

    # Add an instruction to hang up if the caller does nothing
    response.hangup()

    # Return the TwiML instructions to Twilio as an XML string
    return str(response)

# (We will add the /handle_recording endpoint later)


# This block runs the server.
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)