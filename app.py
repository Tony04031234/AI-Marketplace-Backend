from flask import Flask, request, jsonify, session
from flask_cors import CORS
from transformers import pipeline, set_seed
import requests
from requests.structures import CaseInsensitiveDict
import tweepy
from PIL import Image
import pytesseract
import werkzeug
from werkzeug.security import generate_password_hash, check_password_hash
from config import (
    TWITTER_API_KEY_CLIENT,
    TWITTER_API_KEY_SECRET,
    TWITTER_ACCESS_TOKEN,
    TWITTER_ACCESS_TOKEN_SECRET,
    FLASK_SECRET_KEY,
    OPENAI_API_KEY,
    QUERY_URL_NAME,
)

app = Flask(__name__)
CORS(app, resources={r'*': {'origins': '*'}})

app.secret_key = FLASK_SECRET_KEY  #
api_key = OPENAI_API_KEY
QUERY_URL = QUERY_URL_NAME 

@app.route('/api/set_api_key', methods=['POST'])
def set_api_key():
    # Validate user's credentials
    username = request.json.get('username')
    password = request.json.get('password')
    api_key = request.json.get('api_key')

    # In real application, you would fetch user data from a database
    # Here we're using hardcoded example data
    stored_password = 'password'  
    stored_username = 'username'
    if username == stored_username and password == stored_password:
        # If user is valid, store the api_key in server-side session
        session['api_key'] = api_key
        return jsonify({'status': 'success'}), 200
    else: 
        return jsonify({'status': 'error', 'message': 'Invalid credentials'}), 401

def send_tweet(image_url, title, content):
    try:
        auth = tweepy.OAuthHandler(TWITTER_API_KEY_CLIENT, TWITTER_API_KEY_SECRET)
        auth.set_access_token(TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET)
        api = tweepy.API(auth)
        
        print(f"Image URL: {image_url}")
        print(f"Title: {title}")
        print(f"Content: {content}")

        # Download the image from the URL
        response = requests.get(image_url)
        if response.status_code != 200:
            print(f'Error downloading image: {response.reason}')
            return

        # Save the image to a local file
        with open('image.png', 'wb') as f:
            f.write(response.content)

        # Upload the image to Twitter's servers
        try:
            image = api.media_upload('image.png')
        except Exception as e:
            print(f'Error uploading image: {e}')
            return

        # Update the status with the text and image
        try:
            tweet = f"{title}\n{content}"
            api.update_status(status=tweet, media_ids=[image.media_id])
            print("Tweet sent successfully")
        except Exception as e:
            print(f'Error updating status: {e}')
    except Exception as e:
        print(f"Error occurred while sending tweet: {e}")


def generate_header_image(prompt, model, api_key):
    headers = CaseInsensitiveDict()
    headers["Content-Type"] = "application/json"
    api_key = "Bearer " + api_key

    headers["Authorization"] = api_key

    model = "image-alpha-001"
    data = """
    {
        """
    data += f'"model": "{model}",'
    data += f'"prompt": "{prompt}",'
    data += """
        "num_images":1,
        "size":"1024x1024",
        "response_format":"url"
    }
    """

    resp = requests.post(QUERY_URL, headers=headers, data=data)

    if resp.status_code != 200:
        raise ValueError("Failed to generate image")

    response_text = resp.json()
    return response_text['data'][0]['url']

def generate_slides(summary):
    slide_texts = summary.split('\n')
    slides = []

    for text in slide_texts:
        sentences = text.split('. ')
        title = sentences[0].capitalize()
        content = '. '.join(sentences[1:]).capitalize()
        slides.append({
            'title': title,
            'content': content
        })

    return slides

@app.route('/api/generate_presentation', methods=['POST'])
def generate_presentation():
    set_seed(42)  # set a seed for reproducibility
    
    input_text = request.json['inputText']
    summarizer = pipeline('summarization', model='t5-base')
    summary = summarizer(input_text, max_length=100)[0]['summary_text']
    slides = generate_slides(summary)
    header_image = generate_header_image(summary, 'image-alpha-001', api_key)
    try:
        send_tweet(header_image, slides[0]['title'], slides[0]['content'])
    except Exception as e:
        print(f'An error occurred while sending the tweet: {e}')
        print(f'header_image: {header_image}')
        print(f'slides[0]["title"]: {slides[0]["title"]}')
        print(f'slides[0]["content"]: {slides[0]["content"]}')
    return jsonify({ 'slides': slides, 'header_image': header_image })

@app.route('/api/generate_summary', methods=['POST'])
def generate_summary():
    set_seed(42) # set a seed for reproducibility
    input_text = request.json['inputText']
    summarizer = pipeline('summarization', model='t5-base')
    summary = summarizer(input_text, max_length=100)[0]['summary_text']
    return jsonify({ 'summary': summary })

@app.route('/api/generate_code', methods=['POST'])
def generate_code():
    set_seed(42)  # set a seed for reproducibility

    prompt = request.json['prompt']
    code_generator = pipeline('text-generation', model='EleutherAI/gpt-neo-1.3B')
    generated_code = code_generator(prompt, max_length=100, do_sample=True, temperature=0.8)[0]['generated_text']

    return jsonify({'code': generated_code})

def image_to_text(image_file):
    text = pytesseract.image_to_string(Image.open(image_file))
    return text

@app.route('/api/process_image', methods=['POST'])
def process_image():
    image_file = request.files['image']
    filename = werkzeug.utils.secure_filename(image_file.filename)
    image_file.save(filename)
    
    extracted_text = image_to_text(filename)
    # Perform any further analysis on the extracted text as required
    # For example, text summarization, sentiment analysis, etc.

    return jsonify({ 'text': extracted_text, 'analysis': 'your_analysis_here' })



if __name__ == '__main__':
    app.run(debug=True, port=8000)
