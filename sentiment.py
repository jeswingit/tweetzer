"""VADER sentiment analysis for tweets with explainability."""
import re

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

_analyzer = SentimentIntensityAnalyzer()


def _classify(compound: float) -> str:
    """Classify compound score as positive, negative, or neutral."""
    if compound > 0.05:
        return "positive"
    if compound < -0.05:
        return "negative"
    return "neutral"


def _get_contributing_words(text: str) -> list[tuple[str, float]]:
    """Extract words from text that appear in VADER lexicon with their scores."""
    words = re.findall(r"\b[\w']+\b", text, re.IGNORECASE)
    contributing = []
    seen = set()
    for word in words:
        key = word.lower()
        if key in seen:
            continue
        if key in _analyzer.lexicon:
            score = _analyzer.lexicon[key]
            contributing.append((word, score))
            seen.add(key)
    return sorted(contributing, key=lambda x: abs(x[1]), reverse=True)


def analyze_tweets(tweets: list[str]) -> dict:
    """
    Analyze sentiment of a list of tweets with full explainability data.

    Args:
        tweets: List of tweet text strings.

    Returns:
        Dict with keys:
        - positive, negative, neutral: counts
        - avg_score: average compound score
        - tweet_scores: list of dicts with text, compound, label, pos, neg, neu,
          contributing_words
    """
    if not tweets:
        return {
            "positive": 0,
            "negative": 0,
            "neutral": 0,
            "avg_score": 0.0,
            "tweet_scores": [],
        }

    tweet_scores = []
    total = 0.0
    counts = {"positive": 0, "negative": 0, "neutral": 0}

    for text in tweets:
        scores = _analyzer.polarity_scores(text)
        compound = scores["compound"]
        label = _classify(compound)
        contributing = _get_contributing_words(text)
        tweet_scores.append(
            {
                "text": text,
                "compound": compound,
                "label": label,
                "pos": scores["pos"],
                "neg": scores["neg"],
                "neu": scores["neu"],
                "contributing_words": contributing,
            }
        )
        total += compound
        counts[label] += 1

    return {
        "positive": counts["positive"],
        "negative": counts["negative"],
        "neutral": counts["neutral"],
        "avg_score": total / len(tweets),
        "tweet_scores": tweet_scores,
    }
