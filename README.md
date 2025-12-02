# Tee Time Bot

A Python bot for automating login and interactions with Cypress Lake CC's Clubhouse Online portal.

## Features

- Automated login to Cypress Lake CC Member Central
- Headless browser support
- Secure credential management via environment variables
- Extensible architecture for adding more features

## Setup Instructions

### 1. Create Virtual Environment

```bash
cd /Users/patrick/pythonProjects/MarcosTeeTimeBot
python3 -m venv venv
```

### 2. Activate Virtual Environment

```bash
source venv/bin/activate
```

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Credentials

Create a `.env` file in the project root (copy from `.env.example`):

```bash
cp .env.example .env
```

Edit `.env` and add your credentials:

```
CLUBHOUSE_USERNAME=your_username
CLUBHOUSE_PASSWORD=your_password
CLUBHOUSE_URL=https://cypresslakecc.clubhouseonline-e3.com/Member-Central
```

⚠️ **Never commit the `.env` file to git** - it contains sensitive credentials.

## Running the Bot

### Quick Start

```bash
# Activate virtual environment (if not already activated)
source venv/bin/activate

# Run the bot
python clubhouse_bot.py
```

### Deactivate Virtual Environment

When you're done:

```bash
deactivate
```

## Usage

### Basic Login

```python
from clubhouse_bot import ClubhouseBot

# Create bot instance
bot = ClubhouseBot(headless=True)  # headless=True for background mode

# Login
if bot.login():
    print("Successfully logged in!")
    # Perform other actions here
    page_content = bot.get_page_content()
else:
    print("Login failed")

# Close browser
bot.close()
```

### Running in Headless Mode

Set `headless=True` when creating the bot for background operation:

```python
bot = ClubhouseBot(headless=True)
```

## Project Structure

```
MarcosTeeTimeBot/
├── README.md                 # This file
├── requirements.txt          # Python dependencies
├── .env.example             # Example environment variables
├── .env                     # Your credentials (DO NOT COMMIT)
├── clubhouse_bot.py         # Main bot module
└── .gitignore              # Git ignore rules
```

## Requirements

- Python 3.7+
- Chrome/Chromium browser
- Active Cypress Lake CC membership account

## Troubleshooting

### Bot can't find login fields
- The website structure may have changed
- Inspect the page manually to find the correct field selectors
- Update the XPath/selector in `clubhouse_bot.py`

### Login fails but credentials are correct
- Check if Clubhouse Online has changed their login mechanism
- Try running in non-headless mode to see what's happening
- Look for CAPTCHA or additional verification

### ChromeDriver issues
- The `webdriver-manager` package should handle this automatically
- If issues persist, ensure Chrome is installed on your system

## Extending the Bot

To add more features:

1. Add new methods to the `ClubhouseBot` class
2. Use `self.driver` to interact with the page
3. Use `WebDriverWait` and explicit waits for reliability

Example:

```python
def book_tee_time(self, date, time):
    """Book a tee time"""
    # Implement booking logic here
    pass
```

## Legal Notice

Use this bot responsibly and in accordance with Cypress Lake CC's terms of service. Ensure you have permission to automate interactions with their website.
