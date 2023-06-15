import os
import json
from google.oauth2.service_account import Credentials
import openai
import gradio as gr
from gtts import gTTS
from google.cloud import translate_v2 as translate
import random

# Set OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")  # please insert the actual API key here

# Extract service account key from environment variable
raw_service_account_key = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
if raw_service_account_key is None:
    raise ValueError("The GOOGLE_APPLICATION_CREDENTIALS_JSON environment variable is not set.")

# Parse the JSON service account key
service_account_key = json.loads(raw_service_account_key)

# Create the credentials object
credentials = Credentials.from_service_account_info(service_account_key)

# Initialize Google Translate client with the credentials
translate_client = translate.Client(credentials=credentials)

# Function to translate text to Japanese
def translate_text(text, target="ja"):
    if text is None:
        return None
    result = translate_client.translate(text, target_language=target)
    return result["input"], result["translatedText"]

# Function to generate a situation
def generate_situation():
    situations_en = [
        "At the airport trying to book a flight to Japan",
        "At the hotel trying to check-in",
        "At the restaurant trying to order food",
        "Asking for directions to a nearby tourist attraction",
    ]
    situation = random.choice(situations_en)
    return situation

# Maintain a conversation history
conversation_history = []

# Function for conversation with ChatGPT
def chat(situation, user_input):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{'role': 'system', 'content': f'You are a helpful assistant that speaks English and can understand the context. The current situation is: {situation}. Try to respond in under 50 characters.'}] + [{'role': m['role'], 'content': m['content']} for m in conversation_history],
        temperature=0.5,
        max_tokens=200
    )
    conversation_history.append({'role': 'assistant', 'content': response["choices"][0]["message"]["content"]})
    return response["choices"][0]["message"]["content"]

# Function to convert speech to text (using Whisper API)
def speech_to_text(input_audio):
    if not os.path.exists(input_audio):
        raise ValueError("The audio file does not exist.")
    audio_file = open(input_audio, "rb")
    response = openai.Audio.transcribe(
        "whisper-1", audio_file
    )
    audio_file.close()
    return response["text"]

# Function to convert text to speech
def text_to_speech(input_text):
    tts = gTTS(text=input_text, lang="en")
    mp3_filename = "response.mp3"
    tts.save(mp3_filename)
    return mp3_filename  # returns the path of the audio file

# User's next possible response generation function
def generate_user_response(situation, chat_gpt_response):
    prompt = f"The assistant said: '{chat_gpt_response}' to the user in a situation where they are '{situation}'.\n\nWhat might the user reply in under 20 characters:"
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        temperature=0.5,
        max_tokens=20
    )
    return response.choices[0].text.strip()

# Voice Chat function
def voice_chat(input_audio, user_text, situation, get_suggested_response):
    if user_text:
        user_input = user_text
    else:
        user_input = speech_to_text(input_audio)

    # Add user's message to the conversation history
    conversation_history.append({'role': 'user', 'content': user_input})

    # Generate assistant's response and add it to the conversation history
    response_text = chat(situation, user_text)
    response_audio = text_to_speech(response_text)

    # Generate the next user's response if necessary
    if get_suggested_response:
        next_user_response = generate_user_response(situation, response_text)
    else:
        next_user_response = ''

    # Generate the conversation history with translations
    conversation_history_str = '\n'.join([f"{m['role']}: {m['content']} ({translate_text(m['content'])[1]})" for m in conversation_history if m['content']])
    next_user_response_ja = translate_text(next_user_response)[1]

    return response_audio, conversation_history_str, f"{next_user_response} ({next_user_response_ja})"

# Modify Gradio interface
iface_voice_chat = gr.Interface(
    fn=voice_chat,
    inputs=[gr.inputs.Audio(source="microphone", type="filepath"), gr.inputs.Textbox(default="", label="Text Input"), gr.inputs.Textbox(default=generate_situation(), label="Situation"), gr.inputs.Checkbox(label="Generate Suggested User Response")],
    outputs=[gr.outputs.Audio(type="filepath"), gr.outputs.Textbox(label="Chat History (English and Japanese)"), gr.outputs.Textbox(label="Suggested User Response (English and Japanese)")],
    title="Voice Chat with ChatGPT",
    description="Speak or write to the chatbot and have a conversation in English!",
)

iface_voice_chat.launch()

