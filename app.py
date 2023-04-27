from flask import Flask, request, jsonify
from flask_cors import CORS
from transformers import pipeline, set_seed
import requests
from requests.structures import CaseInsensitiveDict
import tweepy


app = Flask(__name__)
CORS(app, resources={r'*': {'origins': '*'}})

api_key = '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'
QUERY_URL = "https://api.openai.com/v1/images/generations"



def send_tweet(image_url, title, content):
    try:
        auth = tweepy.OAuthHandler('7eDkwEelSCyHwbTsfCAMOibuc', 'tsSGW8gNO0glGIy1mKkTR5jcLg83GciAIEUVnxTau6WczAoF5h')
        auth.set_access_token('1651360062714298370-Qkg4ysQql5sBxL0iWweSKdRft9jEbP', 'mmy18kThfSPhosHuXgBMYVRG7uCNxLqsYrTThi2s6IRzk')
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

if __name__ == '__main__':
    app.run(debug=True, port=8000)
