import os
import logging
from clubhouse_bot import get_next_saturday
from config_reader import get_config_from_sheets, get_default_config
from parallel_booking import run_parallel_booking

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

    Spawns parallel browser instances to book tee times concurrently.
    """
    try:
        logger.info("Starting Clubhouse bot from Lambda (parallel mode)")

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

        # Run parallel booking
        record_video = bool(os.environ.get('S3_VIDEO_BUCKET'))
        tee_time_open = event.get('tee_time_open', '06:00')
        result = run_parallel_booking(
            config,
            headless=True,
            record_video=record_video,
            tee_time_open=tee_time_open,
        )
        result["date"] = str(get_next_saturday())

        if result["booked_count"] == result["requested"]:
            logger.info(f"Success! Booked all {result['requested']} requested tee times")
        elif result["booked_count"] > 0:
            logger.warning(f"Partial success: booked {result['booked_count']}/{result['requested']} tee times")
        else:
            logger.warning(f"Failed to book any tee times")

        return result

    except Exception as e:
        logger.exception("Unexpected error in Lambda handler")
        return {
            "status": "error",
            "reason": str(e),
            "booked": [],
            "unavailable": [],
        }
