import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Venice AI API Key (previously MOR)
VENICE_API_KEY = os.getenv("VENICE_API_KEY")
