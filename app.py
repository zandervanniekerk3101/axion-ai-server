import os
from flask import Flask, request, Response
from twilio.twiml.voice_response import VoiceResponse
import openai
import logging

# Set up proper logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
# Note: In Render, these are set in the dashboard, not from a .env file
openai.api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)

# --- Main Routes ---

@app.route('/')
def home():
    return "Axiom AI Server is online!"

@app.route('/ask', methods=['POST'])
def ask_axiom():
    # This is your existing code for handling questions from the app
    data = request.get_json()
    if not data or 'prompt' not in data:
        return {"error": "Invalid request. A 'prompt' is required."}, 400
    
    user_prompt = data['prompt']
    try:
        completion = openai.chat.completions.create(
            model="gpt-4o-mini-realtime",
            messages=[
                {"role": "system", "content": "You are Axiom AI, a helpful and concise personal assistant."},
                {"role": "user", "content": user_prompt}
            ]
        )
        ai_response = completion.choices[0].message.content
        return {"response": ai_response}
    except Exception as e:
        app.logger.error(f"OpenAI Error: {e}", exc_info=True)
        return {"error": "Error connecting to AI model."}, 500

# --- Twilio Routes ---

@app.route('/incoming_call', methods=['POST'])
def handle_incoming_call():
    """
    Handles incoming calls, greets the user, and starts recording a message.
    """
    try:
        response = VoiceResponse()
        # Use a valid Twilio voice (e.g., "alice")
        response.say('Hello, you have reached Axiom AI. Please leave a message after the beep.', voice='alice')
        
        # Record the user's message and send the result to /handle_recording
        response.record(action='/handle_recording', method='POST', maxLength=20, finishOnKey='*')
        
        return Response(str(response), mimetype='text/xml')
    except Exception as e:
        app.logger.error("!!! INCOMING CALL FAILED !!!", exc_info=True)
        response = VoiceResponse()
        response.say("I'm sorry, an application error has occurred. Goodbye.", voice='alice')
        return Response(str(response), mimetype='text/xml')

@app.route('/handle_recording', methods=['POST'])
def handle_recording():
    """
    Handles the webhook from Twilio after a recording is finished.
    """
    # Get the URL of the new recording from Twilio's request
    recording_url = request.form.get('RecordingUrl')
    
    # Log the URL so you can find your voicemails
    app.logger.info(f"New voicemail recording available at: {recording_url}")
    
    # Respond to the caller
    response = VoiceResponse()
    response.say("Thank you for your message. Goodbye.", voice='alice')
    response.hangup()
    
    return Response(str(response), mimetype='text/xml')

# This block is for local testing and is not used by Render
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)