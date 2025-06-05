import tweepy
import requests
import json
import os
from datetime import datetime
import time
import logging

# Konfiguracja logowania
LOG_FILENAME = 'radar_twitter_bot.log'
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
API_KEY = os.getenv("TWITTER_API_KEY")
API_SECRET = os.getenv("TWITTER_API_SECRET")
ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
ACCESS_TOKEN_SECRET = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")

# Endpoint radar.fun
RADAR_API_TIMEFRAME = "6h" # Można zmienić np. na "1h", "24h"
RADAR_API_URL = f"https://radar.fun/api/tokens/most-called?timeframe={RADAR_API_TIMEFRAME}"

# Interwał sprawdzania i tweetowania (w sekundach)
# 6 godzin = 6 * 60 * 60 sekund
CHECK_INTERVAL_SECONDS = 6 * 3600 

# --- Funkcje ---

def get_top_tokens():
    """Pobiera dane z API radar.fun i zwraca top 3 tokeny."""
    logging.info(f"Fetching top tokens from {RADAR_API_URL}")
    try:
        # UWAGA: verify=False wyłącza weryfikację certyfikatu SSL.
        # Jest to potencjalnie niebezpieczne i powinno być używane tylko jeśli jesteś pewien ryzyka
        # lub w środowisku testowym. W produkcji postaraj się rozwiązać problemy z certyfikatem.
        response = requests.get(RADAR_API_URL, verify=False, timeout=30) # Dodano timeout
        response.raise_for_status()  # Wywoła wyjątek dla kodów błędu HTTP (4xx lub 5xx)
        data = response.json()
        
        if not isinstance(data, list):
            logging.error(f"Unexpected data format from API. Expected list, got {type(data)}.")
            return None

        # Sortujemy tokeny według liczby wywołań w ostatnim okresie (zgodnym z timeframe)
        # Zakładamy, że API zwraca pole 'calls_Xh' gdzie X to wartość z RADAR_API_TIMEFRAME
        sort_key = f"calls_{RADAR_API_TIMEFRAME.replace('h', '')}h" # np. calls_6h
        
        # Sprawdzenie czy klucz sortowania istnieje w pierwszym elemencie (jeśli dane istnieją)
        if data and sort_key not in data[0]:
            logging.warning(f"Sort key '{sort_key}' not found in API response. Falling back to 'calls_1h'. Available keys: {data[0].keys() if data else 'None'}")
            sort_key = 'calls_1h' # Fallback, jeśli klucz dynamiczny nie istnieje

        sorted_tokens = sorted(data, key=lambda x: x.get(sort_key, 0), reverse=True)
        
        # Bierzemy top 3 tokeny
        top_3 = sorted_tokens[:3]
        logging.info(f"Successfully fetched and sorted top {len(top_3)} tokens.")
        return top_3
        
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching data from radar.fun API (RequestException): {e}")
        return None
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON from radar.fun API: {e}")
        return None
    except Exception as e:
        logging.error(f"An unexpected error occurred in get_top_tokens: {e}")
        return None

def format_tweet(top_3_tokens):
    """Formatowanie tweeta z top 3 tokenami."""
    if not top_3_tokens:
        return "Could not retrieve token data at this time. #error"

    # Dynamiczne pobranie klucza dla liczby wywołań
    calls_key = f"calls_{RADAR_API_TIMEFRAME.replace('h', '')}h"

    tweet_lines = [f"💎 Top 3 Most Called Tokens ({RADAR_API_TIMEFRAME} - radar.fun) 💎\n"]
    
    for i, token in enumerate(top_3_tokens, 1):
        # Użyj 'N/A' jako wartości domyślnej, jeśli brakuje danych
        symbol = token.get('symbol', 'N/A')
        address = token.get('address', 'N/A')
        # Użyj dynamicznego klucza do pobrania liczby wywołań, z fallbackiem na 0
        calls = token.get(calls_key, token.get('calls_1h', 0)) # Fallback do calls_1h jeśli dynamiczny nie istnieje
        
        # Format: "1. $SYMBOL"
        tweet_lines.append(f"{i}. ${symbol}")
        # Format: "   Address: {address}"
        tweet_lines.append(f"   Address: {address}")
        # Format: "   Calls: {calls}"
        tweet_lines.append(f"   Calls: {calls}\n") # Dodatkowa nowa linia dla czytelności
    
    tweet_lines.append("Powered by outlight.fun")
    tweet_lines.append("#Crypto #Tokens #TradingSignals") # Dodatkowe hashtagi
    
    return "\n".join(tweet_lines)

def main():
    logging.info("Starting Radar.fun Twitter Bot...")

    # Sprawdzenie, czy wszystkie klucze API są ustawione
    if not all([API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET]):
        logging.error("Twitter API credentials not found in environment variables. Exiting.")
        print("Error: Twitter API credentials (TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET) must be set as environment variables.")
        return

    try:
        client = tweepy.Client(
            consumer_key=API_KEY,
            consumer_secret=API_SECRET,
            access_token=ACCESS_TOKEN,
            access_token_secret=ACCESS_TOKEN_SECRET
        )
        # Weryfikacja poświadczeń (opcjonalnie, ale dobrze sprawdzić na starcie)
        me = client.get_me()
        logging.info(f"Successfully authenticated with Twitter as @{me.data.username}")

    except Exception as e:
        logging.error(f"Error creating Twitter client or authenticating: {e}")
        return

    while True:
        try:
            logging.info("Attempting to fetch tokens and tweet...")
            top_3 = get_top_tokens()
            
            if not top_3:
                logging.warning("No token data received. Skipping tweet.")
            else:
                tweet_text = format_tweet(top_3)
                logging.info("Prepared tweet:\n" + "="*20 + f"\n{tweet_text}\n" + "="*20)

                # Wyślij tweet
                response = client.create_tweet(text=tweet_text)
                tweet_id = response.data['id']
                logging.info(f"Tweet sent successfully! Tweet ID: {tweet_id}, Link: https://twitter.com/user/status/{tweet_id}")
            
            logging.info(f"Waiting for {CHECK_INTERVAL_SECONDS // 3600} hours before next cycle...")
            time.sleep(CHECK_INTERVAL_SECONDS)

        except tweepy.TweepyException as e:
            logging.error(f"Twitter API error: {e}")
            # Różne błędy mogą wymagać różnego czasu oczekiwania
            if hasattr(e, 'api_codes') and e.api_codes:
                if 187 in e.api_codes: # Status is a duplicate
                    logging.warning("Tweet is a duplicate. Waiting longer before retrying.")
                    time.sleep(CHECK_INTERVAL_SECONDS // 2) # Poczekaj połowę normalnego interwału
                elif 429 in e.api_codes: # Rate limit
                    logging.warning("Rate limit exceeded. Waiting for 15 minutes.")
                    time.sleep(15 * 60)
                else:
                    time.sleep(5 * 60) # Domyślny czas oczekiwania przy innych błędach Tweepy
            else:
                 time.sleep(5 * 60)
        except Exception as e:
            logging.error(f"An unexpected error occurred in the main loop: {e}")
            logging.info("Waiting for 5 minutes before retrying...")
            time.sleep(300) # 300 sekund = 5 minut

if __name__ == "__main__":
    main()
