import os
import asyncio
from flask import Flask, request, jsonify, render_template, send_from_directory,send_file
from summarization import generate_summary  # Importing the function from summarization.py
from dubbing import *
from werkzeug.utils import secure_filename
import docx2txt
from googletrans import Translator
import fitz  # PyMuPDF

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'translated'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'doc', 'docx'}

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/images/<path:filename>')
def send_image(filename):
    return send_from_directory('images', filename)

@app.route('/dubnow')
def renderDubNow():
    return render_template('dubnow.html')

@app.route('/summarizenow')
def renderSummarization():
    return render_template('summarizenow.html')

@app.route('/smarttranslate')
def renderSmarttranslate():
    return render_template('smarttranslate.html')

@app.route('/process', methods=['POST'])
def process():
    try:
        youtube_url = request.form.get('youtube_url')
        source_lang = request.form.get('source_language')
        target_lang = request.form.get('target_language')
        video_path = None

        if youtube_url:
            video_path = download_youtube_video(youtube_url)
        else:
            video_file = request.files['video']
            os.makedirs("uploads", exist_ok=True)
            video_path = os.path.join("uploads", video_file.filename)
            video_file.save(video_path)

        if not video_path or not os.path.exists(video_path):
            return jsonify({"status": "error", "message": "Failed to obtain video file."})

        final_video_path = process_video_dubbing(video_path, source_lang, target_lang)
        if final_video_path:
            return jsonify({"status": "success", "output_path": final_video_path})
        else:
            return jsonify({"status": "error", "message": "Dubbing failed. Please check the video or transcription process."})

    except Exception as e:
        print(f"Error during video processing: {str(e)}")
        return jsonify({"status": "error", "message": "Error during video processing."})


@app.route('/view/<folder>/<filename>') 
def serve_doc(folder,filename): 
    path = os.path.join(folder, filename)
    with open(path, 'r',encoding='utf-8') as file:
            text = file.read()
            print(text)
    return render_template('renderPDF.html',data=text)


@app.route('/video/downloads/<filename>') 
def serve_video(filename): 
    files = os.listdir("downloads")
    print(f"found files {files}")
    return send_from_directory("downloads", filename)

@app.route('/generate_summary', methods=['POST'])
async def generate_summary_route():
    data = request.json
    video_url = data.get('video_url', '')
    target_language = data.get('target_language', 'en')

    if not video_url:
        return jsonify({"status": "error", "message": "YouTube URL is required"}), 400

    try:
        print("Calling generate_summary with video_url:", video_url, "and target_language:", target_language)
        summary, translated_summary = await generate_summary(video_url, target_language)
        if not summary:
            raise Exception("Summary generation failed")
        return jsonify({"status": "success", "english_summary": summary, "translated_summary": translated_summary})
    except Exception as e:
        print(f"Error during summary generation: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

# Smart Translation
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def extract_text_from_pdf(pdf_path):
    text = ''
    try:
        print("pdf path: ",pdf_path)
        doc = fitz.open(pdf_path)
        print("doc value: ",doc)
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)  # Iterate over each page
            text += page.get_text()  # Extract text from the page

    except Exception as e:
        print(f"Error extracting text from PDF: {str(e)}")
    return text

def extract_text_from_word(doc_path):
    try:
        return docx2txt.process(doc_path)
    except Exception as e:
        print(f"Error extracting text from Word document: {str(e)}")
        return ""

@app.route('/process_translation', methods=['POST'])
def process_translation():
    try:
        if 'document' not in request.files:
            print("No document part")
            return jsonify(status='error', message='No document part')
        
        file = request.files['document']
        target_language = request.form.get('target_language')

        if file.filename == '':
            print("No selected document")
            return jsonify(status='error', message='No selected document')

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # filename=file.filename
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            print(f"File saved at {file_path}")

            if filename.endswith('.pdf'):
                text = extract_text_from_pdf(file_path)
            else:
                text = extract_text_from_word(file_path)
            print(f"Extracted text: {text[:100]}")  # Print first 100 characters of text

            translator = Translator()
            translated_text = translator.translate(text, dest=target_language).text
            print(f"Translated text: {translated_text[:100]}")  # Print first 100 characters of translated text

            output_filename = f'{filename}'
            output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)

            with open(output_path, 'w', encoding='utf-8') as file:
                file.write(translated_text)

            return jsonify(status='success', output_path=output_path)
        else:
            print("Invalid file type")
            return jsonify(status='error', message='Invalid file type')
    except Exception as e:
        print(f"Error during translation process: {str(e)}")
        return jsonify(status='error', message='Error during translation process.')

# Ensure folders exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

if __name__ == '__main__':
    app.run(debug=True)
