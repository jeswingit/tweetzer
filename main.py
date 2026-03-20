"""Entry point for Tweetzer - sTwitter Hashtag Sentiment Analysis."""
import sys

from config import validate_config
from gui import main as gui_main


def main() -> None:
    is_valid, error = validate_config()
    if not is_valid:
        print(error, file=sys.stderr)
        sys.exit(1)
    gui_main()


if __name__ == "__main__":
    main()
