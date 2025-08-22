import os
from flask import Flask, request, jsonify, Response
from dotenv import load_dotenv
import openai
from services.twilio_service import make_phone_call
from twilio.twiml.voice_response import VoiceResponse
import logging # NEW import for logging

# --- NEW: Set up proper logging ---
logging.basicConfig(level=logging.INFO)

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
app = Flask(__name__)

@app.route('/')
def home():
    return "Axiom AI Server is online!"

@app.route('/ask', methods=['POST'])
def ask_axiom():
    # (Your existing ask_axiom code is here)
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
        app.logger.error(f"Error communicating with OpenAI: {e}") # Use logger
        return jsonify({"error": "Sorry, I'm having trouble connecting to my brain right now."}), 500

@app.route('/make_call', methods=['POST'])
def handle_make_call():
    # (Your existing handle_make_call code is here)
    data = request.json
    if not data or 'to_number' not in data or 'message' not in data:
        return jsonify({"error": "Invalid request. 'to_number' and 'message' are required."}), 400
    to_number = data['to_number']
    message = data['message']
    result = make_phone_call(to_number, message)
    return jsonify({"status": result})

@app.route('/incoming_call', methods=['POST'])
def handle_incoming_call():
    """
    This endpoint now uses the logging module to guarantee we see the error.
    """
    try:
        response = VoiceResponse()
        response.say('Hello, you have reached Axiom AI. Please leave a message after the beep.', voice='Polly.Joanna')
        response.record(action='/handle_recording', method='POST', maxLength=20, finishOnKey='*')
        response.hangup()
        return Response(str(response), mimetype='text/xml')
    except Exception as e:
        # --- THIS IS THE CRITICAL CHANGE ---
        # Instead of print(), we use app.logger.error() to log the full traceback.
        app.logger.error("!!! INCOMING CALL FAILED !!!", exc_info=True)
        
        # Respond with a generic error message for Twilio
        response = VoiceResponse()
        response.say("I'm sorry, an application error has occurred. Goodbye.", voice='Polly.Joanna')
        return Response(str(response), mimetype='text/xml')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)