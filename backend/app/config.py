import os

from dotenv import load_dotenv

load_dotenv()

# "fake" (default) answers from app/fake_provider.py with no network access;
# "venice" calls the Venice AI API and needs VENICE_API_KEY.
PROVIDER = os.getenv("DOORMAN_PROVIDER", "fake").strip().lower()
if PROVIDER not in {"fake", "venice"}:
    raise RuntimeError("DOORMAN_PROVIDER must be 'fake' or 'venice'")

VENICE_API_KEY = os.getenv("VENICE_API_KEY")
