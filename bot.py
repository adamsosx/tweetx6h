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
        logging.StreamHandler() # Dodatkowo loguje na konsolę
    ]
)

# Klucze API ładowane ze zmiennych środowiskowych
API_KEY_ENV = os.getenv("TWITTER_API_KEY")
API_SECRET_ENV = os.getenv("TWITTER_API_SECRET")
ACCESS_TOKEN_ENV = os.getenv("TWITTER_ACCESS_TOKEN")
ACCESS_TOKEN_SECRET_ENV = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")

RADAR_API_URL = "https://radar.fun/api/tokens/most-called?timeframe=6h"

def get_top_tokens():
    """Pobiera dane z API radar.fun i zwraca top 3 tokeny."""
    try:
        response = requests.get(RADAR_API_URL, verify=False, timeout=30)
        response.raise_for_status()  # Wywoła wyjątek dla kodów błędu HTTP 4xx/5xx
        data = response.json()
        
        if not isinstance(data, list):
            logging.error(f"API response from radar.fun is not a list, got: {type(data)}. Content: {data}")
            return None

        # Sortujemy tokeny według liczby unikalnych kanałów
        sorted_tokens = sorted(data, key=lambda x: x.get('unique_channels', 0), reverse=True)
        
        # Bierzemy top 3 tokeny
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
        logging.error(f"Unexpected error in get_top_tokens: {e}")
        return None

def format_main_tweet(top_3_tokens):
    """Format tweet with top 3 tokens and 'Source' indicator."""
    tweet = "Top3 Most Called Tokens (6h)\n\n"
    
    for i, token in enumerate(top_3_tokens, 1):
        calls = token.get('unique_channels', 0)
        symbol = token.get('symbol', 'Unknown')
        address = token.get('address', 'No Address Provided') 
        
        tweet += f"{i}. ${symbol}\n"
        tweet += f"   {address}\n"
        tweet += f"   {calls} calls\n\n"
    
    tweet += "Source 👇" # Zgodnie z drugim skryptem
    
    return tweet

def format_reply_tweet():
    """Format the reply tweet with the link."""
    return "🔗 https://outlight.fun/\n#SOL #Outlight"
    
def main():
    logging.info(f"Starting X Bot (single run for scheduled task, timeframe: 6h)...")
    
    # Sprawdzenie kluczy API
    if not all([API_KEY_ENV, API_SECRET_ENV, ACCESS_TOKEN_ENV, ACCESS_TOKEN_SECRET_ENV]):
        logging.error("Twitter API credentials not found in environment variables. Exiting.")
        exit(1)

    # Inicjalizacja klienta Tweepy v2
    try:
        client = tweepy.Client(
            consumer_key=API_KEY_ENV,
            consumer_secret=API_SECRET_ENV,
            access_token=ACCESS_TOKEN_ENV,
            access_token_secret=ACCESS_TOKEN_SECRET_ENV
        )
        # Weryfikacja autentykacji
        me = client.get_me()
        if me and me.data:
            logging.info(f"Successfully authenticated with Twitter as @{me.data.username}")
        else:
            logging.error(f"Failed to authenticate with Twitter. Response: {me}")
            exit(1)
    except Exception as e:
        logging.error(f"Error creating Twitter client or authenticating: {e}")
        exit(1)

    try:
        # Pobierz top 3 tokeny
        top_3 = get_top_tokens()
        if not top_3:
            logging.error("Failed to fetch or process token data. Exiting without tweeting.")
            exit(1) 

        # Utwórz główny tweet
        main_tweet_text = format_main_tweet(top_3)
        logging.info("Prepared main tweet:\n" + "="*20 + f"\n{main_tweet_text}\n" + "="*20)

        # Wyślij główny tweet
        response_main_tweet = client.create_tweet(text=main_tweet_text)
        main_tweet_id = response_main_tweet.data['id']
        main_tweet_user = me.data.username
        logging.info(f"Main tweet sent successfully! Tweet ID: {main_tweet_id}, Link: https://twitter.com/{main_tweet_user}/status/{main_tweet_id}")
        
        # Utwórz i wyślij tweet-odpowiedź
        reply_tweet_text = format_reply_tweet()
        logging.info("Prepared reply tweet:\n" + "="*20 + f"\n{reply_tweet_text}\n" + "="*20)
        
        response_reply_tweet = client.create_tweet(
            text=reply_tweet_text,
            in_reply_to_tweet_id=main_tweet_id
        )
        reply_tweet_id = response_reply_tweet.data['id']
        logging.info(f"Reply tweet sent successfully! Tweet ID: {reply_tweet_id}, Link: https://twitter.com/{main_tweet_user}/status/{reply_tweet_id}")
        
    except tweepy.TweepyException as e:
        # Logowanie bardziej szczegółowych błędów API Twittera
        if hasattr(e, 'api_codes') and hasattr(e, 'api_errors'):
             logging.error(f"Twitter API error during tweet process: {e}. Codes: {e.api_codes}, Errors: {e.api_errors}, Response: {e.response}")
        else:
            logging.error(f"Twitter API error during tweet process: {e}")
        exit(1)
    except Exception as e:
        logging.error(f"An unexpected error occurred in the main task: {e}", exc_info=True) # exc_info=True doda traceback
        exit(1)

    logging.info("X Bot (single run) finished successfully.")

if __name__ == "__main__":
    main()
