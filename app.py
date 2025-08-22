# app.py
# This is the complete code for your Axiom AI server with both AI and Twilio capabilities.

import os
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import openai

# --- NEW IMPORT ---
# Import the function we created to handle making phone calls
from services.twilio_service import make_phone_call

# Load the environment variables (like your API keys) from the .env file
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

# --- NEW ENDPOINT FOR MAKING CALLS ---
@app.route('/make_call', methods=['POST'])
def handle_make_call():
    """
    This endpoint receives a phone number and a message from the app
    and uses Twilio to make the call.
    """
    data = request.json
    if not data or 'to_number' not in data or 'message' not in data:
        return jsonify({"error": "Invalid request. 'to_number' and 'message' are required."}), 400

    to_number = data['to_number']
    message = data['message']

    # Call our function from the twilio_service
    result = make_phone_call(to_number, message)

    return jsonify({"status": result})


# This block runs the server.
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
