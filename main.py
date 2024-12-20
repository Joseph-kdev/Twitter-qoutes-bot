from flask import Flask, jsonify, render_template
from text_cleaner import read_json_file, write_json_file
import tweepy
import json
import schedule
import time
import logging
import os
from datetime import datetime
import threading

app = Flask(__name__)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('quote_bot.log'),
        logging.StreamHandler()
    ]
)

def create_api():
    """
    Create Twitter API client using OAuth 2.0 authentication
    """
    client = tweepy.Client(
        consumer_key=os.getenv("TWITTER_API_KEY"),
        consumer_secret=os.getenv("TWITTER_API_SECRET"),
        access_token=os.getenv("TWITTER_ACCESS_TOKEN"),
        access_token_secret=os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
    )
    return client

class TweetThreadHandler:
    def __init__(self, client):
        self.client = client
        self.TWEET_LIMIT = 280
        
    def post_quote_thread(self, quote, page):
        full_text = quote
        if page != 0:
            full_text = f"{quote}  - The Letters of a Stoic, page:{page}"
            
        chunks = self._split_into_tweets(full_text)
        
        try:
            # Post initial tweet
            response = self.client.create_tweet(text=chunks[0])
            tweets = [response]
            previous_tweet_id = response.data['id']
            
            # Post the rest as replies
            for chunk in chunks[1:]:
                response = self.client.create_tweet(
                    text=chunk,
                    in_reply_to_tweet_id=previous_tweet_id
                )
                tweets.append(response)
                previous_tweet_id = response.data['id']
                
            return tweets
        except tweepy.errors.TweepyException as e:
            logging.error(f"Error posting tweet: {str(e)}")
            return None
    
    def _split_into_tweets(self, text):
        if len(text) <= self.TWEET_LIMIT:
            return [text]
            
        chunks = []
        words = text.split()
        current_chunk = []
        current_length = 0
        
        for word in words:
            if current_length + len(word) + 1 <= self.TWEET_LIMIT:
                current_chunk.append(word)
                current_length += len(word) + 1
            else:
                chunks.append(' '.join(current_chunk))
                current_chunk = [word]
                current_length = len(word) + 1
                
        if current_chunk:
            chunks.append(' '.join(current_chunk))
            
        return chunks

def read_quote():
    try:
        # Create thread handler instance
        thread_handler = TweetThreadHandler(client)
        
        # Load quotes and tweeted data
        quotes = read_json_file("./data/data.json")
        tweeted = read_json_file("./data/tweeted.json")
        
        # Iterate through all quotes to find one not yet tweeted
        for quote in quotes:
            if quote not in tweeted:
                logging.info(f"Posting new quote: {quote}")
                
                quote_text = quote["Quote"]
                page = quote["Page"]
                
                # Post the quote
                tweets = thread_handler.post_quote_thread(quote_text, page)
                
                if tweets:
                    # Add the quote to the tweeted list
                    tweeted.append(quote)
                    write_json_file("./data/tweeted.json", tweeted)
                    logging.info("Quote posted successfully")
                    return {"success": True, "quote": quote}
        
        logging.info("All quotes have been tweeted")
        return {"success": False, "error": "All quotes have been tweeted"}
        
    except Exception as e:
        logging.error(f"Error in read_quote: {str(e)}")
        return {"success": False, "error": str(e)}

def daily_task():
    """Function that will be run daily"""
    logging.info("Starting daily quote tweet task")
    result = read_quote()
    if result["success"]:
        logging.info(f"Daily task completed successfully. Posted quote: {result['quote']}")
    else:
        logging.warning(f"Daily task failed: {result.get('error', 'Unknown error')}")
    return result

def run_scheduler():
    """Run the scheduler in a separate thread"""
    schedule.every().day.at("08:00").do(daily_task)
    while True:
        schedule.run_pending()
        time.sleep(60)

# Create API client
client = create_api()

# Flask routes
@app.route('/')
def home():
    """Home page with basic statistics"""
    try:
        with open("./data/data.json", "r", encoding="utf-8") as f:
            quotes = json.load(f)
        with open("./data/tweeted.json", "r", encoding="utf-8") as f:
            tweeted = json.load(f)
        
        stats = {
            "total_quotes": len(quotes),
            "tweeted_quotes": len(tweeted),
            "remaining_quotes": len(quotes) - len(tweeted),
            "last_tweet_time": datetime.fromtimestamp(
                os.path.getmtime("./data/tweeted.json")
            ).strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return render_template('index.html', stats=stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/post-quote', methods=['POST'])
def post_quote():
    """Endpoint to manually trigger a quote post"""
    result = read_quote()
    return jsonify(result)

@app.route('/stats')
def get_stats():
    """Get current statistics"""
    try:
        with open("./data/data.json", "r", encoding="utf-8") as f:
            quotes = json.load(f)
        with open("./data/tweeted.json", "r", encoding="utf-8") as f:
            tweeted = json.load(f)
        
        return jsonify({
            "total_quotes": len(quotes),
            "tweeted_quotes": len(tweeted),
            "remaining_quotes": len(quotes) - len(tweeted)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    # Start the scheduler in a separate thread
    scheduler_thread = threading.Thread(target=run_scheduler)
    scheduler_thread.daemon = True
    scheduler_thread.start()
    
    # Run the Flask app
    app.run(debug=True, host='0.0.0.0', port=5000)