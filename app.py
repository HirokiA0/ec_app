import openai
import streamlit as st
from gtts import gTTS
import random
import os

# Set OpenAI API key
openai.api_key = "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"  # please insert the actual API key here

# Function to translate text to Japanese
def translate_to_japanese(input_text):
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=f"{input_text}\n\nTranslate the above English text to Japanese:",
        temperature=0.3,
        max_tokens=100
    )
    return response.choices[0].text.strip()

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
    conversation_history.append({'role': 'user', 'content': f'{user_input}'})
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{'role': 'system', 'content': f'You are a helpful assistant that speaks English and can understand the context. The current situation is: {situation}.'}] + [{'role': m['role'], 'content': m['content']} for m in conversation_history],
        temperature=0.5,
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
    prompt = f"The assistant said: '{chat_gpt_response}' to the user in a situation where they are '{situation}'.\n\nWhat might the user reply:"
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        temperature=0.4,
        max_tokens=100
    )
    return response.choices[0].text.strip()

# Modify voice chat function
def voice_chat(input_audio, input_text, situation, get_suggested_response):
    user_text = speech_to_text(input_audio) if input_audio else input_text
    if user_text == '':
        raise ValueError("No input provided.")
    response_text = chat(situation, user_text)
    response_audio = text_to_speech(response_text)
    if get_suggested_response:
        next_user_response = generate_user_response(situation, response_text)
        next_user_response_ja = translate_to_japanese(next_user_response)
    else:
        next_user_response = ''
        next_user_response_ja = ''
    conversation_history_translated = [(m['role'] + ": " + m['content'] + " (" + translate_to_japanese(m['content']) + ")") for m in conversation_history]
    return response_audio, '\n'.join(conversation_history_translated), next_user_response + " (" + next_user_response_ja + ")"

def main():
    st.title("Voice Chat with ChatGPT")
    st.write("Speak or write to the chatbot and have a conversation in English!")

    # The inputs
    input_audio = st.file_uploader("Upload an audio file", type=["mp3", "wav"])
    input_text = st.text_input("Text Input", "")
    situation = st.text_input("Situation", generate_situation())
    get_suggested_response = st.checkbox("Generate Suggested User Response")

    if st.button("Start Chat"):
        if input_audio or input_text:
            response_audio, chat_history, suggested_response = voice_chat(input_audio, input_text, situation, get_suggested_response)
            st.audio(response_audio, format='audio/mp3')
            st.write("Chat History with Translations:")
            st.write(chat_history)
            st.write("Suggested User Response:")
            st.write(suggested_response)
        else:
            st.write("Please provide an audio file or text input to start the chat.")

if __name__ == "__main__":
    main()
