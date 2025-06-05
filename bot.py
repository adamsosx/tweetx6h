import tweepy
import requests
import json
import os
from datetime import datetime
# import time # Usunięty, bo niepotrzebny dla jednorazowego uruchomienia
import logging

# Konfiguracja logowania
LOG_FILENAME = 'bot.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILENAME),
        logging.StreamHandler() # Dodatkowo loguje do konsoli
    ]
)

# --- Konfiguracja ---
# Klucze API Twittera - odczytywane ze zmiennych środowiskowych
API_KEY_ENV = os.getenv("TWITTER_API_KEY")
API_SECRET_ENV = os.getenv("TWITTER_API_SECRET")
ACCESS_TOKEN_ENV = os.getenv("TWITTER_ACCESS_TOKEN")
ACCESS_TOKEN_SECRET_ENV = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")

# Endpoint radar.fun
RADAR_API_TIMEFRAME = "6h" # Zgodnie z logiem, endpoint używa timeframe=6h
RADAR_API_URL = f"https://radar.fun/api/tokens/most-called?timeframe={RADAR_API_TIMEFRAME}"

# --- Funkcje ---

def get_top_tokens():
    """Pobiera dane z API radar.fun i zwraca top 3 tokeny."""
    logging.info(f"Fetching top tokens from {RADAR_API_URL}")
    try:
        response = requests.get(RADAR_API_URL, verify=False, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if not isinstance(data, list):
            logging.error(f"Unexpected data format from API. Expected list, got {type(data)}.")
            return None

        if not data: # Sprawdzenie, czy lista nie jest pusta
            logging.warning("Received empty data list from API.")
            return None

        sort_key = 'channel_calls' 
        
        # Sprawdźmy, czy pierwszy element ma klucz sortowania, aby uniknąć błędu przy pustej liście lub złym formacie
        # To sprawdzenie jest bardziej dla pewności, bo wcześniejsze if not data powinno to załatwić.
        if sort_key not in data[0]:
            logging.error(f"Sort key '{sort_key}' not found in the first element of API response. Available keys: {data[0].keys()}")
            # Można rozważyć próbę fallbacku na inny klucz, jeśli to ma sens
            return None 

        # Filtrujemy listę, aby upewnić się, że każdy element ma klucz sortowania i jest to liczba
        # To pomoże uniknąć problemów z porównywaniem, jeśli niektóre wartości nie są numeryczne
        valid_tokens_for_sorting = []
        for token in data:
            if isinstance(token, dict) and isinstance(token.get(sort_key), (int, float)):
                valid_tokens_for_sorting.append(token)
            else:
                logging.warning(f"Token skipped due to missing or non-numeric sort key '{sort_key}': {token.get('symbol', 'Unknown Symbol')}")
        
        if not valid_tokens_for_sorting:
            logging.warning(f"No valid tokens found for sorting with key '{sort_key}'.")
            return None

        # Sortujemy tylko przefiltrowaną listę
        sorted_tokens = sorted(valid_tokens_for_sorting, key=lambda x: x.get(sort_key, 0), reverse=True)
        
        top_3 = sorted_tokens[:3]
        logging.info(f"Successfully fetched and sorted top {len(top_3)} tokens using '{sort_key}'.")
        return top_3
        
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching data from radar.fun API (RequestException): {e}")
        return None
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON from radar.fun API: {e}")
        return None
    except TypeError as e: # Łapiemy konkretnie TypeError, który powodował problem
        logging.error(f"TypeError during sorting or processing: {e}. This might be due to inconsistent data types for the sort key.")
        return None
    except Exception as e:
        logging.error(f"An unexpected error occurred in get_top_tokens: {e}")
        return None

def format_tweet(top_3_tokens):
    """Format tweet with top 3 tokens"""
    # Używamy RADAR_API_TIMEFRAME w nagłówku, aby był zgodny z pobieranymi danymi
    tweet = f"Top3 Most Called Tokens ({RADAR_API_TIMEFRAME})\n\n" 
    
    for i, token in enumerate(top_3_tokens, 1):
        # ZMIANA: Używamy 'channel_calls' do wyświetlania liczby wywołań, dla spójności
        calls = token.get('channel_calls', 0) 
        symbol = token.get('symbol', 'Unknown')
        address = token.get('address', 'No Address Provided') 
        
        tweet += f"{i}. ${symbol}\n"
        tweet += f"   {address}\n"
        tweet += f"   {calls} calls\n\n"
    
    tweet += "\n outlight.fun\n"
    return tweet

def main():
    logging.info(f"Starting X Bot (single run for scheduled task, timeframe: {RADAR_API_TIMEFRAME})...")
    
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

        response = client.create_tweet(text=tweet_text)
        tweet_id = response.data['id']
        logging.info(f"Tweet sent successfully! Tweet ID: {tweet_id}, Link: https://twitter.com/user/status/{tweet_id}")
        
    except tweepy.TweepyException as e:
        logging.error(f"Twitter API error during tweet process: {e}")
        exit(1)
    except Exception as e:
        logging.error(f"An unexpected error occurred in the main task: {e}")
        exit(1)

    logging.info("X Bot (single run) finished successfully.")

if __name__ == "__main__":
    main()
