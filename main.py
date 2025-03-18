from flask import Flask, jsonify, render_template
import tweepy
import json
import schedule
import time
import logging
import os
import datetime
import threading
from flask_sqlalchemy import SQLAlchemy
import pytz

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///quotes.db"
db = SQLAlchemy(app)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('quote_bot.log'),
        logging.StreamHandler()
    ]
)

class Quote(db.Model):
    __tablename__ = "qoutes"
    
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String, nullable=False)
    page = db.Column(db.String)
    tweeted = db.Column(db.Boolean, default=False)
    tweeted_at = db.Column(db.DateTime)
    
    def to_dict(self):
        return {
            'id': self.id,
            'text': self.text,
            'page': self.page,
            'tweeted': self.tweeted,
            'tweeted_at': self.tweeted_at.isoformat() if self.tweeted_at else None,
        }
        
with app.app_context():
    db.create_all()

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

def post_quote():
    try:
        quote = Quote.query.filter_by(tweeted=False).first()
        
        if not quote:
            logging.info("All qoutes have been tweeted")
            return {"success": False, "error": "All quotes have been tweeted"}
        
        thread_handler = TweetThreadHandler(client)
        
        tweets = thread_handler.post_quote_thread(quote.text, quote.page)
        
        if tweets:
            # Update quote status
            quote.tweeted = True
            quote.tweeted_at = datetime.utcnow()
            db.session.commit()
            logging.info(f"Successfully posted quote ID {quote.id}")
            return {"success": True, "quote": quote.to_dict()}
        else:
            return {"success": False, "error": "Failed to post tweet"}

    except Exception as e:
        db.session.rollback()
        logging.error(f"Error posting quote: {str(e)}")
        return {"success": False, "error": str(e)}
    finally:
        db.session.close()

# Create API client
client = create_api()

# Flask routes
@app.route('/')
def home():
    """Home page with basic statistics"""
    try:
        total_quotes = db.session.query(Quote).count()
        tweeted_quotes = db.session.query(Quote).filter_by(tweeted=True).count()
        last_tweet = db.session.query(Quote).filter_by(tweeted=True)\
            .order_by(Quote.tweeted_at.desc()).first()
        
        stats = {
            "total_quotes": total_quotes,
            "tweeted_quotes": tweeted_quotes,
            "remaining_quotes": total_quotes - tweeted_quotes,
            "last_tweet_time": last_tweet.tweeted_at.strftime('%Y-%m-%d %H:%M:%S') if last_tweet else "Never"
        }
        
        return render_template('index.html', stats=stats)
    finally:
        db.session.close()

@app.route('/post-quote', methods=['POST'])
def trigger_post_quote():
    """Endpoint to manually trigger a quote post"""
    return jsonify(post_quote())

@app.route('/stats')
def get_stats():
    """Get current statistics"""
    try:
        total_quotes = db.session.query(Quote).count()
        tweeted_quotes = db.session.query(Quote).filter_by(tweeted=True).count()
        
        return jsonify({
            "total_quotes": total_quotes,
            "tweeted_quotes": tweeted_quotes,
            "remaining_quotes": total_quotes - tweeted_quotes
        })
    finally:
        db.session.close()

target_time = datetime.time(10,0,0)
current_time = datetime.datetime.now().time()

print(f"Target time: {target_time}")
print(current_time)

if __name__ == "__main__":
    # Run the Flask app
    app.run(debug=True, host='0.0.0.0', port=5000)
    
    if target_time == current_time:
        post_quote()
    
    