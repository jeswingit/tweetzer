"""Tkinter GUI for Tweetzer sentiment analysis app with explainability."""
import threading
import tkinter as tk
from tkinter import ttk, messagebox

from sentiment import analyze_tweets
from twitter_client import TwitterClientError, fetch_tweets_by_hashtag


def _truncate(text: str, max_len: int = 60) -> str:
    """Truncate text for list display."""
    text = text.replace("\n", " ")
    return (text[: max_len - 3] + "...") if len(text) > max_len else text


def run_analysis(app: "TweetzerApp", hashtag: str) -> None:
    """Background worker: fetch tweets and analyze sentiment."""
    try:
        app.root.after(0, lambda: app.set_status("Fetching..."))
        tweets = fetch_tweets_by_hashtag(hashtag)
        app.root.after(0, lambda: app.set_status("Analyzing..."))
        result = analyze_tweets(tweets)
        app.root.after(0, lambda: app.show_results(result))
    except TwitterClientError as e:
        msg = str(e) or "Unknown Twitter API error"
        app.root.after(0, lambda m=msg: app.show_error(m))
    except Exception as e:
        msg = str(e) or f"Unexpected error: {type(e).__name__}"
        app.root.after(0, lambda m=msg: app.show_error(m))


def _show_explanation_popup(parent: tk.Tk, tweet_data: dict) -> None:
    """Show a popup explaining why the tweet was categorized as it was."""
    popup = tk.Toplevel(parent)
    popup.title("Sentiment Explanation")
    popup.geometry("500x450")
    popup.transient(parent)
    popup.grab_set()

    # Main frame with padding
    frame = ttk.Frame(popup, padding=15)
    frame.pack(fill=tk.BOTH, expand=True)

    # Tweet text
    ttk.Label(frame, text="Tweet:", font=("", 10, "bold")).pack(anchor=tk.W)
    text_frame = ttk.Frame(frame)
    text_frame.pack(fill=tk.X, pady=(5, 15))
    tweet_text = tk.Text(text_frame, wrap=tk.WORD, height=4, width=60)
    tweet_text.pack(fill=tk.X)
    tweet_text.insert(tk.END, tweet_data["text"])
    tweet_text.config(state=tk.DISABLED)

    # Classification
    label = tweet_data["label"].upper()
    ttk.Label(frame, text=f"Classification: {label}", font=("", 11, "bold")).pack(
        anchor=tk.W, pady=(0, 5)
    )

    # Score breakdown
    compound = tweet_data["compound"]
    pos, neg, neu = tweet_data["pos"], tweet_data["neg"], tweet_data["neu"]
    threshold = "> 0.05" if label == "POSITIVE" else "< -0.05" if label == "NEGATIVE" else "between -0.05 and 0.05"
    ttk.Label(
        frame,
        text=f"Compound score: {compound:.3f} (classified as {label} because {compound:.3f} is {threshold})",
    ).pack(anchor=tk.W)
    ttk.Label(frame, text=f"Positive proportion: {pos:.2%} | Negative: {neg:.2%} | Neutral: {neu:.2%}").pack(
        anchor=tk.W, pady=(0, 15)
    )

    # Contributing words
    contributing = tweet_data.get("contributing_words", [])
    ttk.Label(frame, text="Words that influenced the score (from VADER lexicon):", font=("", 10, "bold")).pack(
        anchor=tk.W
    )
    if contributing:
        words_text = ", ".join(
            f'"{w}" ({s:+.2f})' for w, s in contributing[:15]
        )
        if len(contributing) > 15:
            words_text += f" ... and {len(contributing) - 15} more"
        ttk.Label(frame, text=words_text, wraplength=460).pack(
            anchor=tk.W, pady=(5, 0)
        )
        ttk.Label(
            frame,
            text="(Positive scores add to sentiment; negative scores subtract)",
            font=("", 8),
        ).pack(anchor=tk.W, pady=(5, 0))
    else:
        ttk.Label(frame, text="No sentiment words from the lexicon found in this tweet.").pack(
            anchor=tk.W, pady=(5, 0)
        )

    ttk.Button(frame, text="Close", command=popup.destroy).pack(pady=(20, 0))
    popup.wait_window()


class TweetzerApp:
    """Main application window."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self._tweet_data: list[dict] = []
        root.title("Tweetzer - Hashtag Sentiment Analysis")
        root.geometry("600x500")
        root.minsize(400, 350)

        input_frame = ttk.Frame(root, padding=10)
        input_frame.pack(fill=tk.X)
        ttk.Label(input_frame, text="Hashtag:").pack(side=tk.LEFT, padx=(0, 5))
        self.hashtag_var = tk.StringVar()
        self.hashtag_entry = ttk.Entry(
            input_frame, textvariable=self.hashtag_var, width=30
        )
        self.hashtag_entry.pack(side=tk.LEFT, padx=(0, 10))
        self.hashtag_entry.insert(0, "e.g. Python")
        self.hashtag_entry.bind("<FocusIn>", self._clear_placeholder)
        self.fetch_btn = ttk.Button(
            input_frame, text="Fetch & Analyze", command=self._on_fetch
        )
        self.fetch_btn.pack(side=tk.LEFT)

        self.status_var = tk.StringVar(value="Enter a hashtag and click Fetch.")
        status_label = ttk.Label(root, textvariable=self.status_var)
        status_label.pack(pady=(0, 5))

        self.summary_var = tk.StringVar()
        summary_label = ttk.Label(
            root, textvariable=self.summary_var, font=("", 10, "bold")
        )
        summary_label.pack(pady=5)

        list_frame = ttk.Frame(root, padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(list_frame, text="Tweets (click one for explanation):").pack(anchor=tk.W)
        list_container = ttk.Frame(list_frame)
        list_container.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        scrollbar = ttk.Scrollbar(list_container)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tweet_listbox = tk.Listbox(
            list_container,
            height=15,
            selectmode=tk.SINGLE,
            yscrollcommand=scrollbar.set,
            font=("Consolas", 9),
        )
        self.tweet_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.tweet_listbox.yview)
        self.tweet_listbox.bind("<<ListboxSelect>>", self._on_tweet_select)

    def _clear_placeholder(self, event: tk.Event) -> None:
        if self.hashtag_var.get().strip() == "e.g. Python":
            self.hashtag_entry.delete(0, tk.END)

    def _on_tweet_select(self, event: tk.Event) -> None:
        selection = self.tweet_listbox.curselection()
        if not selection or not self._tweet_data:
            return
        idx = selection[0]
        if 0 <= idx < len(self._tweet_data):
            _show_explanation_popup(self.root, self._tweet_data[idx])

    def set_status(self, msg: str) -> None:
        self.status_var.set(msg)

    def show_error(self, msg: str) -> None:
        if not msg or str(msg).strip() == "None":
            msg = "An unknown error occurred. Check your API credentials and access level."
        self.status_var.set(f"Error: {msg}")
        self.summary_var.set("")
        self.tweet_listbox.delete(0, tk.END)
        self._tweet_data = []
        self.fetch_btn.config(state=tk.NORMAL)
        messagebox.showerror("Error", msg)

    def show_results(self, result: dict) -> None:
        pos = result["positive"]
        neg = result["negative"]
        neu = result["neutral"]
        avg = result["avg_score"]
        self.status_var.set("Done")
        self.summary_var.set(
            f"Positive: {pos} | Negative: {neg} | Neutral: {neu} | Avg: {avg:.2f}"
        )

        self.tweet_listbox.delete(0, tk.END)
        self._tweet_data = result["tweet_scores"]
        for item in result["tweet_scores"]:
            short = _truncate(item["text"])
            self.tweet_listbox.insert(tk.END, f"[{item['label'].upper()}] {short}")
        self.fetch_btn.config(state=tk.NORMAL)

    def _on_fetch(self) -> None:
        hashtag = self.hashtag_var.get().strip()
        if not hashtag:
            messagebox.showwarning("Warning", "Please enter a hashtag.")
            return
        if hashtag == "e.g. Python":
            hashtag = "Python"
        self.fetch_btn.config(state=tk.DISABLED)
        self.set_status("Fetching...")
        thread = threading.Thread(target=run_analysis, args=(self, hashtag))
        thread.daemon = True
        thread.start()


def main() -> None:
    root = tk.Tk()
    app = TweetzerApp(root)
    root.mainloop()
