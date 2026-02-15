import speech_recognition as sr
from gtts import gTTS
from playsound3 import playsound
from markdown_text_clean import clean_text as md_clean_text
import subprocess
import os
import sys

# --- CONFIGURATION ---
WAKE_WORD = "nexus"
PICOCLAW_CMD = ["/home/rpi2/rpiclaw/picoclaw", "agent", "-m"]

def clean_for_speech(text):
    """Strips emojis and special characters so gTTS doesn't read them aloud"""
    # Drops all non-ASCII characters (which includes all emojis)
    cleaned = text.encode('ascii', 'ignore').decode('ascii')
    cleaned = md_clean_text(cleaned)
    return cleaned.strip()

def speak(text):
    """Generates an MP3 using Google TTS and plays it via mpg321"""
    clean_text = clean_for_speech(text)

    # If the response was ONLY an emoji (rare, but possible), don't try to speak an empty string
    if not clean_text:
        return

    print(f"🗣️ PicoClaw: {clean_text}")
    try:
        # Request the audio from Google
        tts = gTTS(text=clean_text, lang='en', slow=False)
        tts.save("response.mp3")
        
        # Play the audio using the system's lightweight mp3 player
        # subprocess.run(["play", "response.mp3"])
        playsound("response.mp3")
        
        # Clean up the file so we don't fill up the SD card
        os.remove("response.mp3")
    except Exception as e:
        print(f"TTS Error: {e}")

def ask_picoclaw(prompt):
    """Sends the command to the local PicoClaw agent"""
    print("🧠 Thinking...")
    try:
        result = subprocess.run(
            PICOCLAW_CMD + [prompt],
            capture_output=True, 
            text=True
        )
        reply = result.stdout.strip()
        
        if reply:
            speak(reply)
        else:
            speak("I'm sorry, my brain didn't return an answer.")
            
    except Exception as e:
        print(f"Error calling PicoClaw: {e}")
        speak("I encountered an error connecting to my core.")

def main():
    recognizer = sr.Recognizer()
    recognizer.pause_threshold = 2.0  # wait few seconds before concluding spoken text
    
    with sr.Microphone() as source:
        print("🎧 Calibrating background noise... shhh...")
        recognizer.adjust_for_ambient_noise(source, duration=2)
        print(f"✅ Ready! Say '{WAKE_WORD}' to trigger.")
        
        while True:
            try:
                print("👂 Listening...")
                # phrase_time_limit stops it from recording endlessly if there's background noise
                audio = recognizer.listen(source, timeout=8, phrase_time_limit=15)
                
                # Send the audio to Google for transcription
                text = recognizer.recognize_google(audio).lower()
                print(f"Heard: '{text}'")
                
                if WAKE_WORD in text:
                    # Strip the wake word out to isolate the command
                    command = text.replace(WAKE_WORD, "").strip()
                    
                    if command:
                        # The user said the whole sentence at once (e.g., "Jarvis turn on the light")
                        ask_picoclaw(command)
                    else:
                        # The user just said "Jarvis"
                        speak("Yes?")
                        
                        print("👂 Waiting for command...")
                        # Give the user 5 seconds to start speaking their question
                        cmd_audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
                        cmd_text = recognizer.recognize_google(cmd_audio)
                        print(f"Command heard: '{cmd_text}'")
                        
                        ask_picoclaw(cmd_text)
                        
            except sr.WaitTimeoutError:
                pass # Expected if no one is talking after waking it up
            except sr.UnknownValueError:
                pass # Google couldn't understand the audio, ignore silently
            except sr.RequestError as e:
                print(f"🌐 Network Error: {e}")
                # We can't use gTTS to say there is a network error, so we print it.
            except Exception as e:
                print(f"Unexpected Error: {e}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nShutting down voice interface...")
        sys.exit(0)
