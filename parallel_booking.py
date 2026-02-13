"""
Parallel booking coordinator for TeeTimeBot.

Spawns N worker threads (one per tee time to book), each with its own
ClubhouseBot browser instance. Workers pull preferences from a shared
thread-safe queue and attempt to book. If a preference is unavailable,
the worker grabs the next one from the queue.
"""

import os
import queue
import threading
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict
from zoneinfo import ZoneInfo

from clubhouse_bot import ClubhouseBot, get_next_saturday
from config_reader import TeeTimeConfig

ET = ZoneInfo("America/New_York")


def _upload_video_to_s3(local_path: str, worker_id: int):
    """Upload a video file to S3 if S3_VIDEO_BUCKET is configured."""
    bucket = os.environ.get("S3_VIDEO_BUCKET")
    if not bucket or not local_path:
        return

    try:
        import boto3

        next_sat = get_next_saturday()
        s3_key = f"videos/{next_sat}/worker-{worker_id}.webm"

        s3 = boto3.client("s3")
        s3.upload_file(local_path, bucket, s3_key)
        print(f"[Worker-{worker_id}] Video uploaded to s3://{bucket}/{s3_key}")
    except Exception as e:
        print(f"[Worker-{worker_id}] Failed to upload video to S3: {e}")


@dataclass
class BookingCoordinator:
    """Thread-safe coordinator for parallel booking."""

    preference_queue: queue.Queue
    target_bookings: int
    lock: threading.Lock = field(default_factory=threading.Lock)
    booking_count: int = 0
    results: List[Dict] = field(default_factory=list)
    errors: List[Dict] = field(default_factory=list)

    def record_success(self, worker_id: int, pref, guests_added: int):
        with self.lock:
            self.booking_count += 1
            self.results.append({
                "worker": worker_id,
                "time": pref.time,
                "hole": pref.hole,
                "holes_to_play": pref.holes_to_play,
                "transport": pref.transport,
                "priority": pref.priority,
                "guests_added": guests_added,
            })

    def record_failure(self, worker_id: int, pref, reason: str):
        with self.lock:
            self.errors.append({
                "worker": worker_id,
                "time": pref.time if pref else "N/A",
                "hole": pref.hole if pref else "N/A",
                "priority": pref.priority if pref else "N/A",
                "reason": reason,
            })

    def target_reached(self) -> bool:
        with self.lock:
            return self.booking_count >= self.target_bookings


def _parse_open_time(tee_time_open: str):
    """Parse tee time open string (HH:MM format)."""
    parts = tee_time_open.split(":")
    return int(parts[0]), int(parts[1])


def _wait_until_open(tag: str, tee_time_open: str):
    """Sleep until tee times open at the configured time in ET."""
    open_hour, open_minute = _parse_open_time(tee_time_open)
    now = datetime.now(ET)
    target = now.replace(hour=open_hour, minute=open_minute, second=0, microsecond=0)
    delta = (target - now).total_seconds()
    period = "AM" if open_hour < 12 else "PM"
    display_hour = open_hour % 12 or 12
    target_str = f"{display_hour}:{str(open_minute).zfill(2)} {period} ET"
    if delta > 0:
        print(f"{tag} Waiting {delta:.1f}s until {target_str}...")
        time.sleep(delta)
        print(f"{tag} Go time! {datetime.now(ET).strftime('%H:%M:%S.%f')}")
    else:
        print(f"{tag} Already past {target_str}, proceeding immediately")


def booking_worker(
    worker_id: int,
    coordinator: BookingCoordinator,
    headless: bool = True,
    record_video: bool = False,
    tee_time_open: str = "06:00",
):
    """
    Worker function that runs in its own thread.

    Creates its own ClubhouseBot, logs in, navigates to tee times,
    then pulls preferences from the shared queue until it books one
    or all preferences are exhausted.
    """
    bot = None
    tag = f"[Worker-{worker_id}]"

    try:
        print(f"{tag} Starting bot...")
        bot = ClubhouseBot(headless=headless, record_video=record_video, name=tag)

        if not bot.login():
            print(f"{tag} Login failed, exiting")
            coordinator.record_failure(worker_id, None, "login_failed")
            return

        print(f"{tag} Logged in successfully")

        if not bot.navToTeeTimes():
            print(f"{tag} Navigation to Tee Times failed, exiting")
            coordinator.record_failure(worker_id, None, "navigation_failed")
            return

        next_sat = get_next_saturday()
        el = bot.find_date_element(
            next_sat.day, next_sat.month, next_sat.year, click=True
        )
        if not el:
            print(f"{tag} Date element not found for {next_sat}, exiting")
            coordinator.record_failure(worker_id, None, "date_not_found")
            return

        print(f"{tag} Ready on {next_sat}, positioned on tee times page")

        # Wait until tee times open
        _wait_until_open(tag, tee_time_open)

        # Re-click the date to refresh tee time availability after opening
        bot.find_date_element(
            next_sat.day, next_sat.month, next_sat.year, click=True
        )
        time.sleep(2)

        # Pull preferences from the shared queue and attempt booking
        while not coordinator.target_reached():
            try:
                pref = coordinator.preference_queue.get_nowait()
            except queue.Empty:
                print(f"{tag} No more preferences available")
                break

            print(
                f"{tag} Trying pref {pref.priority}: "
                f"{pref.time} Hole {pref.hole} ({pref.holes_to_play} holes)"
            )

            if bot.select_tee_time(pref.time, pref.hole):
                guests_added = bot.add_guests_to_booking(
                    "Guest, TBD",
                    num_guests=3,
                    holes_to_play=pref.holes_to_play,
                    transport=pref.transport,
                )
                coordinator.record_success(worker_id, pref, guests_added)
                print(
                    f"{tag} SUCCESS: {pref.time} Hole {pref.hole} "
                    f"({guests_added} guests added)"
                )
                break  # One booking per worker
            else:
                coordinator.record_failure(worker_id, pref, "unavailable")
                print(f"{tag} UNAVAILABLE: {pref.time} Hole {pref.hole}")

    except Exception as e:
        print(f"{tag} Unexpected error: {e}")
        traceback.print_exc()

    finally:
        if bot:
            try:
                bot.close()
                if bot.video_path:
                    _upload_video_to_s3(bot.video_path, worker_id)
            except Exception:
                pass


def run_parallel_booking(
    config: TeeTimeConfig,
    headless: bool = True,
    record_video: bool = False,
    tee_time_open: str = "06:00",
) -> Dict:
    """
    Orchestrate parallel booking of tee times.

    Spawns one worker thread per tee time to book. Each worker gets its
    own browser instance and pulls preferences from a shared queue.

    Returns a result dict with booking outcomes.
    """
    n = config.tee_times_to_book
    prefs = config.preferences

    if n <= 0 or len(prefs) == 0:
        return {
            "status": "error",
            "reason": "no preferences or zero bookings requested",
            "requested": n,
            "booked_count": 0,
            "booked": [],
            "unavailable": [],
        }

    coordinator = BookingCoordinator(
        preference_queue=queue.Queue(),
        target_bookings=n,
    )

    # Load all preferences into the queue in priority order
    for pref in prefs:
        coordinator.preference_queue.put(pref)

    # Spawn workers (cap at number of available preferences)
    num_workers = min(n, len(prefs))
    print(f"Spawning {num_workers} parallel booking workers for {n} tee times")

    threads = []
    for i in range(num_workers):
        t = threading.Thread(
            target=booking_worker,
            args=(i + 1, coordinator, headless, record_video, tee_time_open),
            name=f"BookingWorker-{i + 1}",
        )
        threads.append(t)
        t.start()

    # Wait for all threads (with timeout to avoid hanging in Lambda)
    deadline = time.time() + 160
    for t in threads:
        remaining = max(0, deadline - time.time())
        t.join(timeout=remaining)

    return {
        "status": "ok" if coordinator.booking_count >= n else "partial",
        "requested": n,
        "booked_count": coordinator.booking_count,
        "booked": coordinator.results,
        "unavailable": coordinator.errors,
    }
