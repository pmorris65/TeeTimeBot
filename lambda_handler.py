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
        if not el:
            logger.warning("Date element not found")
            return {"status": "error", "action": "date_not_found", "date": str(next_sat)}

        logger.info(f"Found and clicked date element for {next_sat}")

        # Try to select the 8:07 AM Hole 10 tee time
        import time
        time.sleep(3)  # Wait for tee times to load

        if bot.select_tee_time("8:07", 10):
            logger.info("Successfully selected 8:07 AM Hole 10 tee time")
            return {"status": "ok", "action": "tee_time_selected", "date": str(next_sat), "time": "8:07", "hole": 10}
        else:
            logger.warning("8:07 AM Hole 10 tee time not available")
            return {"status": "ok", "action": "tee_time_unavailable", "date": str(next_sat), "time": "8:07", "hole": 10}

    except Exception as e:
        logger.exception("Unexpected error in Lambda handler")
        return {"status": "error", "reason": str(e)}

    finally:
        if bot:
            try:
                bot.close()
            except Exception:
                pass
