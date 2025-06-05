import tweepy
import requests
import json
import os
from datetime import datetime
import logging

# Konfiguracja logowania
LOG_FILENAME = 'bot.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILENAME),
        logging.StreamHandler()
    ]
)

API_KEY_ENV = os.getenv("TWITTER_API_KEY")
API_SECRET_ENV = os.getenv("TWITTER_API_SECRET")
ACCESS_TOKEN_ENV = os.getenv("TWITTER_ACCESS_TOKEN")
ACCESS_TOKEN_SECRET_ENV = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")

RADAR_API_URL = "https://radar.fun/api/tokens/most-called?timeframe=6h"

def get_top_tokens():
    try:
        response = requests.get(RADAR_API_URL, verify=False, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if not isinstance(data, list):
            logging.error(f"API response is not a list, got: {type(data)}. Content: {data}")
            return None

        sorted_tokens = sorted(data, key=lambda x: x.get('unique_channels', 0), reverse=True)
        
        top_3 = sorted_tokens[:3]
        return top_3
    except requests.exceptions.HTTPError as e:
        logging.error(f"HTTP error fetching data from radar.fun API: {e}. Response: {e.response.text if e.response else 'N/A'}")
        return None
    except requests.exceptions.RequestException as e:
        logging.error(f"Request error fetching data from radar.fun API: {e}")
        return None
    except json.JSONDecodeError as e:
        logging.error(f"JSON decode error from radar.fun API: {e}. Response text: {response.text if 'response' in locals() else 'N/A'}")
        return None
    except Exception as e:
        logging.error(f"Error in get_top_tokens: {e}")
        return None

def format_tweet(top_3_tokens):
    tweet = "Top3 Most Called Tokens (6h)\n\n"
    
    for i, token in enumerate(top_3_tokens, 1):
        calls = token.get('unique_channels', 0)
        symbol = token.get('symbol', 'Unknown')
        address = token.get('address', 'No Address Provided') 
        
        tweet += f"{i}. ${symbol}\n"
        tweet += f"   {address}\n"
        tweet += f"   {calls} calls\n\n"
    
    tweet += "\n outlight.fun\n"
    
    return tweet

def main():
    logging.info(f"Starting X Bot (single run for scheduled task, timeframe: 6h)...")
    
    if not all([API_KEY_ENV, API_SECRET_ENV, ACCESS_TOKEN_ENV, ACCESS_TOKEN_SECRET_ENV]):
        logging.error("Twitter API credentials not found in environment variables. Exiting.")
        exit(1)

    try:
        client = tweepy.Client(
            consumer_key=API_KEY_ENV,
            consumer_secret=API_SECRET_ENV,
            access_token=ACCESS_TOKEN_ENV,
            access_token_secret=ACCESS_TOKEN_SECRET_ENV
        )
        me = client.get_me()
        logging.info(f"Successfully authenticated with Twitter as @{me.data.username}")
    except Exception as e:
        logging.error(f"Error creating Twitter client or authenticating: {e}")
        exit(1)

    try:
        top_3 = get_top_tokens()
        if not top_3:
            logging.error("Failed to fetch or process token data. Exiting without tweeting.")
            exit(1) 

        tweet_text = format_tweet(top_3)
        logging.info("Prepared tweet:\n" + "="*20 + f"\n{tweet_text}\n" + "="*20)

        response_tweet = client.create_tweet(text=tweet_text)
        tweet_id = response_tweet.data['id']
        logging.info(f"Tweet sent successfully! Tweet ID: {tweet_id}, Link: https://twitter.com/{me.data.username}/status/{tweet_id}")
        
    except tweepy.TweepyException as e:
        logging.error(f"Twitter API error during tweet process: {e}")
        exit(1)
    except Exception as e:
        logging.error(f"An unexpected error occurred in the main task: {e}")
        exit(1)

    logging.info("X Bot (single run) finished successfully.")

if __name__ == "__main__":
    main()
