import os
import time
import logging
from clubhouse_bot import ClubhouseBot, get_next_saturday
from config_reader import get_config_from_sheets, get_default_config, TeeTimeConfig

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, context):
    """
    AWS Lambda handler to run the bot on schedule.

    Environment variables expected:
      - CLUBHOUSE_USERNAME
      - CLUBHOUSE_PASSWORD
      - CLUBHOUSE_URL (optional, default already in clubhouse_bot)
      - GOOGLE_CREDENTIALS (JSON string of service account credentials)
      - GOOGLE_SHEET_ID (the spreadsheet ID)

    This function reads tee time preferences from Google Sheets and
    attempts to book the requested number of tee times.
    """
    bot = None
    booked_times = []
    failed_times = []

    try:
        logger.info("Starting Clubhouse bot from Lambda")

        # Load configuration from Google Sheets
        sheet_id = os.environ.get('GOOGLE_SHEET_ID')
        if sheet_id:
            try:
                config = get_config_from_sheets(sheet_id)
                logger.info(f"Loaded config: book {config.tee_times_to_book} times, {len(config.preferences)} preferences")
            except Exception as e:
                logger.warning(f"Failed to load Google Sheets config: {e}. Using defaults.")
                config = get_default_config()
        else:
            logger.info("No GOOGLE_SHEET_ID set, using default config")
            config = get_default_config()

        # Instantiate bot in headless mode
        bot = ClubhouseBot(headless=True)

        if not bot.login():
            logger.error("Login failed")
            return {"status": "error", "reason": "login_failed"}

        # Navigate to tee times
        if not bot.navToTeeTimes():
            logger.error("Failed to navigate to tee times")
            return {"status": "error", "reason": "navigation_failed"}

        # Compute next Saturday
        next_sat = get_next_saturday()
        logger.info(f"Next Saturday: {next_sat}")

        # Attempt to find and click the next Saturday
        el = bot.find_date_element(next_sat.day, next_sat.month, next_sat.year, click=True, timeout=8)
        if not el:
            logger.warning("Date element not found")
            return {"status": "error", "action": "date_not_found", "date": str(next_sat)}

        logger.info(f"Found and clicked date element for {next_sat}")
        time.sleep(3)  # Wait for tee times to load

        # Try to book tee times from preferences
        times_to_book = config.tee_times_to_book
        logger.info(f"Attempting to book {times_to_book} tee times from {len(config.preferences)} preferences")

        for pref in config.preferences:
            if len(booked_times) >= times_to_book:
                logger.info(f"Reached target of {times_to_book} bookings, stopping")
                break

            logger.info(f"Trying preference {pref.priority}: {pref.time} Hole {pref.hole} ({pref.holes_to_play} holes)")

            if bot.select_tee_time(pref.time, pref.hole):
                booked_times.append({
                    "time": pref.time,
                    "hole": pref.hole,
                    "holes_to_play": pref.holes_to_play,
                    "priority": pref.priority
                })
                logger.info(f"Successfully selected: {pref.time} Hole {pref.hole}")
                # TODO: Complete booking with holes_to_play when booking is implemented
            else:
                failed_times.append({
                    "time": pref.time,
                    "hole": pref.hole,
                    "priority": pref.priority
                })
                logger.info(f"Not available: {pref.time} Hole {pref.hole}")

        # Summary
        result = {
            "status": "ok",
            "date": str(next_sat),
            "requested": times_to_book,
            "booked_count": len(booked_times),
            "booked": booked_times,
            "unavailable": failed_times
        }

        if len(booked_times) == times_to_book:
            logger.info(f"Success! Booked all {times_to_book} requested tee times")
        elif len(booked_times) > 0:
            logger.warning(f"Partial success: booked {len(booked_times)}/{times_to_book} tee times")
        else:
            logger.warning(f"Failed to book any tee times from {len(config.preferences)} preferences")

        return result

    except Exception as e:
        logger.exception("Unexpected error in Lambda handler")
        return {
            "status": "error",
            "reason": str(e),
            "booked": booked_times,
            "unavailable": failed_times
        }

    finally:
        if bot:
            try:
                bot.close()
            except Exception:
                pass
