import os
from vosk import Model, KaldiRecognizer
import wave
import numpy as np
from scipy.signal import resample
from flask import Flask, request, jsonify, render_template, send_from_directory
from googletrans import Translator
from yt_dlp import YoutubeDL
from moviepy import VideoFileClip, AudioFileClip, concatenate_audioclips
import subprocess

import pyttsx3
from gtts import gTTS


app = Flask(__name__)

# Initialize the Google Translator
translator = Translator()

# Function to download YouTube video using yt-dlp
def download_youtube_video(youtube_url):
    try:
        print(f"Downloading video from YouTube: {youtube_url}")
        os.makedirs("downloads", exist_ok=True)
        output_template = os.path.join("downloads", "%(title)s.%(ext)s")

        ydl_opts = {
            'format': 'mp4',
            'outtmpl': output_template,
        }

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=True)
            downloaded_file = ydl.prepare_filename(info)
            print(f"Video downloaded to {downloaded_file}")
            return downloaded_file
    except Exception as e:
        print(f"Error downloading video: {str(e)}")
        return None

# Function to extract and resample audio using moviepy and scipy
def extract_audio_with_moviepy(video_path):
    try:
        print(f"Extracting audio from video: {video_path}")
        video = VideoFileClip(video_path)
        audio_path = video_path.replace(".mp4", ".wav")
        temp_audio_path = video_path.replace(".mp4", "_temp.wav")
        video.audio.write_audiofile(temp_audio_path)

        # Resample the audio to 16kHz, mono using scipy
        with wave.open(temp_audio_path, "rb") as in_file:
            params = in_file.getparams()
            audio_frames = in_file.readframes(params.nframes)
            audio_np = np.frombuffer(audio_frames, dtype=np.int16)
            mono_audio = audio_np if params.nchannels == 1 else audio_np[::2]
            resampled_audio = resample(mono_audio, int(len(mono_audio) * 16000 / params.framerate)).astype(np.int16)

        with wave.open(audio_path, "wb") as out_file:
            out_file.setnchannels(1)
            out_file.setsampwidth(params.sampwidth)
            out_file.setframerate(16000)
            out_file.writeframes(resampled_audio.tobytes())

        os.remove(temp_audio_path)  # Clean up temporary file

        print(f"Audio extracted and saved to {audio_path}")
        return audio_path
    except Exception as e:
        print(f"Error extracting audio with moviepy: {str(e)}")
        return None

# Function to transcribe audio using VOSK
def transcribe_audio(audio_path, language_model_path):
    print("Transcribing audio...")
    try:
        with wave.open(audio_path, "rb") as wf:
            if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getframerate() != 16000:
                print("Error: Audio must be 16kHz, mono.")
                return None

            model = Model(language_model_path)
            rec = KaldiRecognizer(model, wf.getframerate())

            final_transcription = []
            while True:
                data = wf.readframes(4000)
                if len(data) == 0:
                    break
                if rec.AcceptWaveform(data):
                    result = rec.Result()
                    text = eval(result).get("text", "")
                    final_transcription.append(text)

            final_result = rec.FinalResult()
            text = eval(final_result).get("text", "")
            final_transcription.append(text)

            transcription = " ".join(final_transcription)
            print(f"Transcription result: {transcription}")
            return transcription
    except Exception as e:
        print(f"Error during transcription: {str(e)}")
        return None

# Function to synthesize speech using AI4Bharat's Kannada TTS model
import subprocess

def synthesize_speech_kannada(text, output_path):
    print(f"Generating speech in Kannada for: {text}...")
    try:
        tts = gTTS(text=text, lang='kn') 
        tts.save(output_path)
        print(f"Speech synthesis saved to {output_path}")
        return True
    except:
        print(f"Error during speech synthesis")
        return False


# Function to synthesize speech using AI4Bharat's Kannada TTS model
def synthesize_speech(text, output_path,lang):
    print(f"Generating speech in Kannada for: {text}...")
    try:
        command = [
            "python",
            "TTS/bin/synthesize.py",
            "--text", text,
            "--out_path", output_path,
            "--model_path", "C:\\Users\\sadan\\Downloads\\kn\\kn\\hifigan\\best_model.pth",
            "--config_path", "C:\\Users\\sadan\\Downloads\\kn\\kn\\hifigan\\config.json"
        ]
        subprocess.run(command, check=True)
        print(f"Speech synthesis saved to {output_path}")
    except subprocess.CalledProcessError as e:
        print(f"Error during speech synthesis: {str(e)}")

# Function to add silence to an audio file
def add_silence(audio_clip, duration):
    silence = AudioFileClip("path_to_silence_file.wav").subclip(0, duration)
    return concatenate_audioclips([audio_clip, silence])

# Function to merge audio and video using moviepy
def merge_audio_video(video_path, audio_path, output_path):
    print(f"Merging audio: {audio_path} with video: {video_path}")
    try:
        video_clip = VideoFileClip(video_path)
        audio_clip = AudioFileClip(audio_path)

        # Check durations
        video_duration = video_clip.duration
        audio_duration = audio_clip.duration
        print(f"Video duration: {video_duration}, Audio duration: {audio_duration}")

        # Pad audio with silence if needed
        if audio_duration < video_duration:
            print("Padding audio with silence...")
            audio_clip = add_silence(audio_clip, video_duration - audio_duration)
        # Trim audio if needed
        elif audio_duration > video_duration:
            print("Trimming audio to match video duration...")
            audio_clip = audio_clip.subclipped(0, video_duration)

        final_clip = video_clip.with_audio(audio_clip)
        final_clip.write_videofile(output_path)
        print(f"Merged video saved to {output_path}")
        return output_path
    except Exception as e:
        print(f"Error merging audio and video: {str(e)}")
        return None

# Function to translate text in chunks
def translate_text_in_chunks(text, source_language, target_language, chunk_size=500):
    try:
        translated_chunks = []
        for i in range(0, len(text), chunk_size):
            chunk = text[i:i+chunk_size]
            if chunk is not None:
                translated_chunk = translator.translate(chunk, src=source_language, dest=target_language).text
                translated_chunks.append(translated_chunk)
        return " ".join(translated_chunks)
    except Exception as e:
        print(f"Error during translation: {e}")
        return None

# Function to process video dubbing
def process_video_dubbing(video_path, source_language, target_language):
    try:
        print(f"Starting the dubbing process for video: {video_path}")
        audio_path = extract_audio_with_moviepy(video_path)
        if not audio_path:
            print("Failed to extract audio")
            return None
        
        dubbed_audio_path = video_path.replace(".mp4", f"_{target_language}_dubbed.wav")
        final_video_path = video_path.replace(".mp4", f"_{target_language}_dubbed.mp4")

        transcript = transcribe_audio(audio_path, "vosk-model-small-en-us-0.15")
        if not transcript:
            print("Failed to transcribe audio")
            return None

        translated_text = translate_text_in_chunks(transcript, source_language, target_language)
        if not translated_text:
            print("Failed to translate text")
            return None
        
        print(f"Translation result: {translated_text}")

        print("target language is ",target_language)

        if target_language == 'kn':
            if not synthesize_speech_kannada(translated_text, dubbed_audio_path):
                return None
        else:
            synthesize_speech(translated_text, dubbed_audio_path, target_language)

        final_video_path = merge_audio_video(video_path, dubbed_audio_path, final_video_path)
        return final_video_path
    except Exception as e:
        print(f"Error during video dubbing: {str(e)}")
        return None

# @app.route('/process', methods=['POST'])
# def process():
#     try:
#         youtube_url = request.form.get('youtube_url')
#         source_lang = request.form['source_language']
#         target_lang = request.form['target_language']
#         video_path = None

#         if youtube_url:
#             video_path = download_youtube_video(youtube_url)
#         else:
#             video_file = request.files['video']
#             os.makedirs("uploads", exist_ok=True)
#             video_path = os.path.join("uploads", video_file.filename)
#             video_file.save(video_path)

#         if not video_path or not os.path.exists(video_path):
#             return jsonify({"status": "error", "message": "Failed to obtain video file."})

#         final_video_path = process_video_dubbing(video_path, source_lang, target_lang)
#         if final_video_path:
#             return jsonify({"status": "success", "output_path": final_video_path})
#         else:
#             return jsonify({"status": "error", "message": "Dubbing failed. Please check the video or transcription process."})


#     except Exception as e:
#         print(f"Error during video processing: {str(e)}")
#         return jsonify({"status": "error", "message": "Error during video processing."})

# @app.route('/video/downloads/<filename>') 
# def serve_video(filename): 
#     print("fetching files")
#     files = os.listdir("downloads")
#     print(f"found files {files}")
#     return send_from_directory("downloads", filename)