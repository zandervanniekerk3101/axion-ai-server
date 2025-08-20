# app.py
# This is the updated code for your Axiom AI server with AI capabilities.

import os
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import openai

# Load the environment variables (like your API key) from the .env file
load_dotenv()

# Set up the OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

# Create an instance of the Flask application
app = Flask(__name__)

# This is the original route to check if the server is online.
@app.route('/')
def home():
    return "Axiom AI Server is online!"

# This is the NEW route that will handle AI requests from your future Android app.
# It only accepts POST requests, which is a standard way to send data to a server.
@app.route('/ask', methods=['POST'])
def ask_axiom():
    # Get the data sent from the app. We expect it to be in JSON format.
    data = request.get_json()

    # Basic error checking to make sure we received a 'prompt'.
    if not data or 'prompt' not in data:
        return jsonify({"error": "Invalid request. A 'prompt' is required."}), 400

    # Extract the user's question/prompt from the JSON data.
    user_prompt = data['prompt']

    try:
        # Send the prompt to the OpenAI API (using the gpt-4o-mini model).
        completion = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are Axiom AI, a helpful and concise personal assistant."},
                {"role": "user", "content": user_prompt}
            ]
        )
        # Extract the AI's response text.
        ai_response = completion.choices[0].message.content
        
        # Send the AI's response back in JSON format.
        return jsonify({"response": ai_response})

    except Exception as e:
        # If something goes wrong with the OpenAI API call, send back an error.
        print(f"Error communicating with OpenAI: {e}")
        return jsonify({"error": "Sorry, I'm having trouble connecting to my brain right now."}), 500

# This block runs the server.
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)