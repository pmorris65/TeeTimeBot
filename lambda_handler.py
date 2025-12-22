import os
import logging
from clubhouse_bot import ClubhouseBot, get_next_saturday

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Lambda expects a handler function named `handler` (or configurable)

def handler(event, context):
    """
    AWS Lambda handler to run the bot on schedule.

    Environment variables expected:
      - CLUBHOUSE_USERNAME
      - CLUBHOUSE_PASSWORD
      - CLUBHOUSE_URL (optional, default already in clubhouse_bot)

    This function runs headless and attempts to log in and click the next Saturday.
    """
    bot = None
    try:
        logger.info("Starting Clubhouse bot from Lambda")

        # Instantiate bot in headless mode
        bot = ClubhouseBot(headless=True)

        if not bot.login():
            logger.error("Login failed")
            return {"status": "error", "reason": "login_failed"}

        # Navigate to tee times (if necessary)
        try:
            bot.navToTeeTimes()
        except Exception:
            logger.warning("navToTeeTimes failed or not required")

        # Compute next Saturday
        next_sat = get_next_saturday()
        logger.info(f"Next Saturday: {next_sat}")

        # Attempt to find and click the next Saturday
        el = bot.find_date_element(next_sat.day, next_sat.month, next_sat.year, click=True, timeout=8)
        if el:
            logger.info("Found and clicked date element")
            # Optionally proceed to booking steps here
            return {"status": "ok", "action": "clicked_date", "date": str(next_sat)}
        else:
            logger.warning("Date element not found")
            return {"status": "ok", "action": "date_not_found", "date": str(next_sat)}

    except Exception as e:
        logger.exception("Unexpected error in Lambda handler")
        return {"status": "error", "reason": str(e)}

    finally:
        if bot:
            try:
                bot.close()
            except Exception:
                pass
