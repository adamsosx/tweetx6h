import tweepy
import time
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
OUTLIGHT_API_URL = "https://old.outlight.fun/api/tokens/most-called?timeframe=6h"

def get_top_tokens():
    """Pobiera dane z API outlight.fun i zwraca top 3 tokeny, licząc tylko kanały z win_rate > 30%"""
    try:
        response = requests.get(OUTLIGHT_API_URL)
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
    # Rotating headers for main tweet
    headers = [
        "🧠 Monty Log Dump - Top Called 6h",
        "🚨 Most Called Tokens 6h",
        "📟 Monty Watch: 6h 📞 Frenzy",
        "🎯 Top Degen Focus (Callers)",
        "🤖 Monty Scraped This for You:",
        "📞 6h Top Called Leaderboard:",
        "📡 Last 10h: Most Called Projects",
        "📞 Degens are loud af Top 6h Calls:",
        "📞 Monty Call Sheet  6h",
        "🚨 6h Top Callers Report"
    ]
    
    # Use current timestamp to rotate headers
    current_hour = datetime.now().hour
    selected_header = headers[current_hour % len(headers)]
    
    tweet = f"{selected_header}\n\n"
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
    tweet += "\n\n1/2"
    return tweet

def format_link_tweet():
    """Format the link tweet (reply)"""
    # Rotating messages for reply tweet
    messages = [
        "Degeneracy is alive and WELL 📞📞📞",
        "Called more than your ex",
        "Is it conviction or just click addiction?",
        "High call count = high cope?",
        "Get in or get laughed at",
        "Chart going up? no clue. calls going beep",
        "Zero fundamentals, max vibes",
        "Calls mean nothing, but they do mean something",
        "Degens only sleep when their wallets do 💤",
        "Nothing but vibes & unpaid interns 📞"
    ]
    
    # Use current minute to rotate messages
    current_minute = datetime.now().minute
    selected_message = messages[current_minute % len(messages)]
    
    return f"2/2\n\n{selected_message}\n\n🧪 Data from: 🔗 https://outlight.fun/\n\n#SOL #Outlight #TokenCalls"

def create_tweets_with_rate_limit(client, tweets_to_send):
    """
    Send tweets with proper rate limiting
    """
    for tweet in tweets_to_send:
        try:
            response = client.create_tweet(text=tweet)
            logging.info(f"Tweet sent successfully: {response.data['id']}")
            # Wait at least 60 seconds between tweets to avoid rate limits
            time.sleep(60)  # 60 seconds = 1 minute
        except tweepy.TooManyRequests as e:
            # Get the reset time from the error response
            reset_time = int(e.response.headers.get('x-rate-limit-reset', 0))
            current_time = int(time.time())
            # Calculate wait time (add 10 seconds buffer)
            wait_time = max(reset_time - current_time + 10, 60)
            
            logging.error(f"Rate limit exceeded. Waiting {wait_time} seconds")
            time.sleep(wait_time)
            # Retry the tweet after waiting
            try:
                response = client.create_tweet(text=tweet)
                logging.info(f"Tweet sent successfully after waiting: {response.data['id']}")
            except Exception as retry_e:
                logging.error(f"Failed to send tweet even after waiting: {retry_e}")
        except Exception as e:
            logging.error(f"Error sending tweet: {e}")
            # Wait before trying the next tweet anyway
            time.sleep(60)

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

        # Wait at least 60 seconds before sending reply
        logging.info("Waiting 60 seconds before sending reply tweet...")
        time.sleep(60)

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

        # Send reply tweet with rate limit handling
        try:
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

        except tweepy.TooManyRequests as e:
            # Obsługa rate limit dla reply tweeta
            reset_time = int(e.response.headers.get('x-rate-limit-reset', 0))
            current_time = int(time.time())
            wait_time = max(reset_time - current_time + 10, 60)
            
            logging.error(f"Rate limit exceeded when sending reply. Waiting {wait_time} seconds before retrying...")
            time.sleep(wait_time)
            
            # Retry sending reply tweet
            try:
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
                logging.info(f"Reply tweet sent successfully after waiting! Tweet ID: {reply_tweet_id}, Link: https://twitter.com/{me.data.username}/status/{reply_tweet_id}")
            except Exception as retry_e:
                logging.error(f"Failed to send reply tweet even after waiting: {retry_e}")

    except tweepy.TooManyRequests as e:
        # Obsługa rate limit dla głównego tweeta
        reset_time = int(e.response.headers.get('x-rate-limit-reset', 0))
        current_time = int(time.time())
        wait_time = max(reset_time - current_time + 10, 60)
        logging.error(f"Rate limit exceeded when sending main tweet. Need to wait {wait_time} seconds before retrying")
        # Tutaj możesz dodać time.sleep(wait_time) i retry logic jeśli chcesz
    except tweepy.TweepyException as e:
        logging.error(f"Twitter API error sending tweet: {e}")
    except Exception as e:
        logging.error(f"Unexpected error sending tweet: {e}")

    logging.info("GitHub Action: Bot execution finished.")

if __name__ == "__main__":
    main()
