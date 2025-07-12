import asyncio
from transformers import pipeline
from youtube_transcript_api import YouTubeTranscriptApi
from googletrans import Translator

# Initialize the summarizer
summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
translator = Translator()

# Function to get transcript from YouTube video
def get_youtube_transcript(video_url):
    try:
        video_id = video_url.split("v=")[-1].split("&")[0]
        if "youtu.be" in video_url:
            video_id = video_url.split("/")[-1].split("?")[0]
        print("Fetching transcript for video_id:", video_id)  # Debugging statement
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        transcript = " ".join([d['text'] for d in transcript_list])
        print("Transcript fetched successfully")  # Debugging statement
        return transcript
    except Exception as e:
        print(f"Error fetching transcript: {str(e)}")
        raise

# Function to chunk the transcript
def chunk_transcript(transcript, chunk_size=1000):
    words = transcript.split()
    return [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]

# Retry mechanism for translation
async def retry_translate(text, dest, attempts=3):
    for attempt in range(attempts):
        try:
            translation = translator.translate(text, dest=dest)
            return translation.text
        except Exception as e:
            print(f"Translation attempt {attempt + 1} failed: {str(e)}")
            if attempt == attempts - 1:
                raise

# Function to generate summary in English and target language
async def generate_summary(video_url, target_language='en'):
    try:
        transcript = get_youtube_transcript(video_url)
        if not transcript:
            raise Exception("Transcript is empty or could not be fetched")

        print("Transcript length:", len(transcript))  # Debugging statement

        chunks = chunk_transcript(transcript, chunk_size=500)
        print("Number of chunks:", len(chunks))  # Debugging statement

        summaries = []
        for index, chunk in enumerate(chunks):
            try:
                summary_result = summarizer(chunk, max_length=130, min_length=30, do_sample=False)
                print(f"Summarization result for chunk {index}:", summary_result)  # Debugging statement

                if not summary_result or len(summary_result) == 0:
                    raise Exception(f"Summarization returned an empty result for chunk {index}")

                summary = summary_result[0].get('summary_text', '')
                if not summary:
                    raise Exception(f"Summarization returned an empty summary text for chunk {index}")

                summaries.append(summary)
            except Exception as chunk_error:
                print(f"Error summarizing chunk {index}: {chunk_error}")

        if not summaries:
            raise Exception("No valid summaries generated")

        combined_summary = " ".join(summaries)
        print("Combined summary generated successfully")  # Debugging statement

        translated_summary = await retry_translate(combined_summary, dest=target_language)
        
        return combined_summary, translated_summary
    except Exception as e:
        print(f"Error generating summary: {str(e)}")
        raise Exception(f"Error generating summary: {str(e)}")
