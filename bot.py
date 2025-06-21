import tweepy
import requests
import json
from datetime import datetime, timezone # Dodano timezone dla UTC
import logging
import os

# Dodane do obsługi uploadu grafiki
from tweepy import OAuth1UserHandler, API

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()] # Logowanie do konsoli/outputu Akcji
)

# Klucze API odczytywane ze zmiennych środowiskowych
api_key = os.getenv("TWITTER_API_KEY")
api_secret = os.getenv("TWITTER_API_SECRET")
access_token = os.getenv("TWITTER_ACCESS_TOKEN")
access_token_secret = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")

# URL API outlight.fun - z pierwszego kodu (6h timeframe)
OUTLIGHT_API_URL = "https://outlight.fun/api/tokens/most-called?timeframe=6h"

def get_top_tokens():
    """Pobiera dane z API outlight.fun i zwraca top 3 tokeny, licząc tylko kanały z win_rate > 30%"""
    try:
        response = requests.get(OUTLIGHT_API_URL, verify=False)
        response.raise_for_status()
        data = response.json()

        tokens_with_filtered_calls = []
        for token in data:
            channel_calls = token.get('channel_calls', [])
            # Licz tylko kanały z win_rate > 30%
            calls_above_30 = [call for call in channel_calls if call.get('win_rate', 0) > 30]
            count_calls = len(calls_above_30)
            if count_calls > 0:
                token_copy = token.copy()
                token_copy['filtered_calls'] = count_calls
                tokens_with_filtered_calls.append(token_copy)

        # Sortuj po liczbie filtered_calls malejąco
        sorted_tokens = sorted(tokens_with_filtered_calls, key=lambda x: x.get('filtered_calls', 0), reverse=True)
        top_3 = sorted_tokens[:3]
        return top_3
    except Exception as e:
        logging.error(f"Unexpected error in get_top_tokens: {e}")
        return None

def format_tweet(top_3_tokens):
    """Format tweet with top 3 tokens (tylko calls z win_rate > 30%)"""
    tweet = f"🚀Top 3 Most 📞 6h\n\n"
    medals = ['🥇', '🥈', '🥉']
    for i, token in enumerate(top_3_tokens, 0):
        calls = token.get('filtered_calls', 0)
        symbol = token.get('symbol', 'Unknown')
        address = token.get('address', 'No Address Provided')
        medal = medals[i] if i < len(medals) else f"{i+1}."
        tweet += f"{medal} ${symbol}\n"
        tweet += f"{address}\n"
        tweet += f"📞 {calls}\n\n"
    tweet = tweet.rstrip('\n')
    return tweet

def format_link_tweet():
    """Format the link tweet (reply)"""
    return "\ud83e\uddea Data from: \ud83d\udd17 https://outlight.fun/\n#SOL #Outlight #TokenCalls "

def main():
    logging.info("GitHub Action: Bot execution started.")

    if not all([api_key, api_secret, access_token, access_token_secret]):
        logging.error("CRITICAL: One or more Twitter API keys are missing from environment variables. Exiting.")
        return

    try:
        # Klient v2 do tweetów tekstowych i odpowiedzi
        client = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_token_secret
        )
        me = client.get_me()
        logging.info(f"Successfully authenticated on Twitter as @{me.data.username}")

        # Klient v1.1 do uploadu grafiki
        auth_v1 = OAuth1UserHandler(api_key, api_secret, access_token, access_token_secret)
        api_v1 = API(auth_v1)
    except tweepy.TweepyException as e:
        logging.error(f"Tweepy Error creating Twitter client or authenticating: {e}")
        return
    except Exception as e:
        logging.error(f"Unexpected error during Twitter client setup: {e}")
        return

    top_3 = get_top_tokens()
    if not top_3: # Obsługuje zarówno None (błąd API) jak i pustą listę (brak tokenów)
        logging.warning("Failed to fetch top tokens or no tokens returned. Skipping tweet.")
        return

    tweet_text = format_tweet(top_3)
    logging.info(f"Prepared main tweet ({len(tweet_text)} chars):")
    logging.info(tweet_text)

    if len(tweet_text) > 280:
        logging.warning(f"Generated main tweet is too long ({len(tweet_text)} chars). Twitter will likely reject it.")
        # Można dodać return, jeśli nie chcemy próbować wysyłać za długiego tweeta
        # return

    try:
        # --- Dodanie grafiki do głównego tweeta ---
        image_path = os.path.join("images", "msgtwt.png")
        if not os.path.isfile(image_path):
            logging.error(f"Image file not found: {image_path}. Sending tweet without image.")
            media_id = None
        else:
            try:
                media = api_v1.media_upload(image_path)
                media_id = media.media_id
                logging.info(f"Image uploaded successfully. Media ID: {media_id}")
            except Exception as e:
                logging.error(f"Error uploading image: {e}. Sending tweet without image.")
                media_id = None

        # Wysyłanie głównego tweeta z grafiką (jeśli się udało)
        if media_id:
            response_main_tweet = client.create_tweet(text=tweet_text, media_ids=[media_id])
        else:
            response_main_tweet = client.create_tweet(text=tweet_text)
        main_tweet_id = response_main_tweet.data['id']
        logging.info(f"Main tweet sent successfully! Tweet ID: {main_tweet_id}, Link: https://twitter.com/{me.data.username}/status/{main_tweet_id}")

        # Przygotowanie i wysłanie tweeta z linkiem jako odpowiedzi (z grafiką)
        link_tweet_text = format_link_tweet()
        logging.info(f"Prepared reply tweet ({len(link_tweet_text)} chars):")
        logging.info(link_tweet_text)

        if len(link_tweet_text) > 280:
            logging.warning(f"Generated reply tweet is too long ({len(link_tweet_text)} chars). Twitter will likely reject it.")
            # Można zdecydować, czy mimo to próbować wysłać, czy pominąć odpowiedź
            # return lub continue w pętli (ale tu nie ma pętli)

        # --- Dodanie grafiki do odpowiedzi ---
        reply_image_path = os.path.join("images", "msgtwtft.png")
        if not os.path.isfile(reply_image_path):
            logging.error(f"Reply image file not found: {reply_image_path}. Sending reply without image.")
            reply_media_id = None
        else:
            try:
                reply_media = api_v1.media_upload(reply_image_path)
                reply_media_id = reply_media.media_id
                logging.info(f"Reply image uploaded successfully. Media ID: {reply_media_id}")
            except Exception as e:
                logging.error(f"Error uploading reply image: {e}. Sending reply without image.")
                reply_media_id = None

        if reply_media_id:
            response_reply_tweet = client.create_tweet(
                text=link_tweet_text,
                in_reply_to_tweet_id=main_tweet_id,
                media_ids=[reply_media_id]
            )
        else:
            response_reply_tweet = client.create_tweet(
                text=link_tweet_text,
                in_reply_to_tweet_id=main_tweet_id
            )
        reply_tweet_id = response_reply_tweet.data['id']
        logging.info(f"Reply tweet sent successfully! Tweet ID: {reply_tweet_id}, Link: https://twitter.com/{me.data.username}/status/{reply_tweet_id}")

    except tweepy.TweepyException as e:
        logging.error(f"Twitter API error sending tweet: {e}")
    except Exception as e:
        logging.error(f"Unexpected error sending tweet: {e}")

    logging.info("GitHub Action: Bot execution finished.")

if __name__ == "__main__":
    # Ostrzeżenie o wyłączeniu weryfikacji SSL, jeśli używane jest `verify=False` w `requests.get`
    if 'requests' in globals() and hasattr(requests, 'packages') and hasattr(requests.packages, 'urllib3'):
        try:
            # Wyłączenie ostrzeżeń InsecureRequestWarning, ponieważ verify=False jest używane celowo (choć niezalecane)
            requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)
            logging.warning("SSL verification is disabled for requests (verify=False). "
                            "This is not recommended for production environments but used here as in the original script.")
        except AttributeError:
            # Na wypadek gdyby struktura requests.packages.urllib3 się zmieniła
            logging.warning("Could not disable InsecureRequestWarning for requests.")
            pass
    main()
