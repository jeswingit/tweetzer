"""Twitter API client for fetching tweets by hashtag."""
from datetime import datetime, timedelta, timezone

import tweepy

from config import get_bearer_token


class TwitterClientError(Exception):
    """Raised when Twitter API calls fail."""

    pass


def _extract_tweepy_message(e: Exception) -> str:
    """Extract a user-friendly message from a Tweepy exception."""
    if hasattr(e, "api_messages") and e.api_messages:
        return "; ".join(str(m) for m in e.api_messages if m)
    msg = str(e)
    return msg if msg and msg != "None" else "Unknown Twitter API error"


def fetch_tweets_by_hashtag(
    hashtag: str, max_results: int = 500, days_back: int = 7
) -> list[str]:
    """Fetch recent tweets containing the given hashtag."""
    token = get_bearer_token()
    if not token:
        raise TwitterClientError("BEARER_TOKEN is not configured.")

    tag = hashtag.strip().lstrip("#")
    if not tag:
        raise TwitterClientError("Hashtag cannot be empty.")

    query = f"#{tag} -is:retweet lang:en"
    now = datetime.now(timezone.utc)
    end_time = now - timedelta(seconds=15)
    start_time = now - timedelta(days=days_back)

    try:
        client = tweepy.Client(bearer_token=token)
        tweets = []
        for tweet in tweepy.Paginator(
            client.search_recent_tweets,
            query,
            max_results=100,
            start_time=start_time.isoformat().replace("+00:00", "Z"),
            end_time=end_time.isoformat().replace("+00:00", "Z"),
            tweet_fields=["created_at"],
            user_fields=["username"],
        ).flatten(limit=max_results):
            tweets.append(tweet.text)
    except tweepy.TooManyRequests as e:
        raise TwitterClientError(
            "Twitter API rate limit exceeded. Please try again later."
        ) from e
    except tweepy.Unauthorized as e:
        raise TwitterClientError(
            "Invalid or expired Bearer Token. Check your .env configuration."
        ) from e
    except tweepy.Forbidden as e:
        raise TwitterClientError(
            _extract_tweepy_message(e)
            or "Access forbidden. Your API tier may not support search."
        ) from e
    except tweepy.BadRequest as e:
        raise TwitterClientError(f"Invalid request: {_extract_tweepy_message(e)}") from e
    except tweepy.NotFound as e:
        raise TwitterClientError(f"Not found: {_extract_tweepy_message(e)}") from e
    except tweepy.TwitterServerError as e:
        raise TwitterClientError(
            f"Twitter server error: {_extract_tweepy_message(e)}"
        ) from e
    except tweepy.TweepyException as e:
        raise TwitterClientError(_extract_tweepy_message(e)) from e
    except Exception as e:
        raise TwitterClientError(
            _extract_tweepy_message(e) or f"Unexpected error: {type(e).__name__}"
        ) from e

    return tweets
