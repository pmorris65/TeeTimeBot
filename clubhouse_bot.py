"""
Clubhouse Online Bot for Cypress Lake CC
Automates login to https://cypresslakecc.clubhouseonline-e3.com/Member-Central
"""

import argparse
import os
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
import time

# Load environment variables
load_dotenv()

def get_next_saturday(from_date=None):
    """
    Return the date (datetime.date) for the next Saturday following `from_date`.

    If `from_date` is None, uses today's date. If `from_date` is a
    `datetime.date` or `datetime.datetime` it's accepted. If `from_date` is
    a string it must be in `YYYY-MM-DD` format.

    The function returns the next Saturday strictly after `from_date`.

    Examples:
        >>> get_next_saturday()
        datetime.date(2025, 12, 13)

    Args:
        from_date (None|str|datetime.date|datetime.datetime): base date

    Returns:
        datetime.date: date object for the next Saturday
    """
    from datetime import date, datetime, timedelta

    if from_date is None:
        base = date.today()
    elif isinstance(from_date, datetime):
        base = from_date.date()
    elif isinstance(from_date, date):
        base = from_date
    elif isinstance(from_date, str):
        try:
            base = datetime.strptime(from_date, "%Y-%m-%d").date()
        except Exception:
            raise ValueError("from_date string must be in YYYY-MM-DD format")
    else:
        raise TypeError("from_date must be None, str, date, or datetime")

    # Python weekday(): Monday=0 ... Sunday=6. Saturday=5
    target_weekday = 5
    days_ahead = (target_weekday - base.weekday() + 7) % 7
    if days_ahead == 0:
        days_ahead = 7  # next Saturday, not today

    return base + timedelta(days=days_ahead)

class ClubhouseBot:
    def __init__(self, headless=False):
        """
        Initialize the Clubhouse bot

        Args:
            headless (bool): Run browser in headless mode (no GUI)
        """
        self.username = os.getenv('CLUBHOUSE_USERNAME')
        self.password = os.getenv('CLUBHOUSE_PASSWORD')
        self.base_url = os.getenv('CLUBHOUSE_URL', 'https://cypresslakecc.clubhouseonline-e3.com/Member-Central')

        if not self.username or not self.password:
            raise ValueError("CLUBHOUSE_USERNAME and CLUBHOUSE_PASSWORD must be set in .env file")

        # Initialize Playwright
        self.playwright = sync_playwright().start()

        # Browser launch args - extra flags needed for Lambda/container environments
        browser_args = [
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-blink-features=AutomationControlled",
            "--disable-gpu",
            "--single-process",
            "--disable-setuid-sandbox",
            "--no-zygote",
        ]

        try:
            self.browser = self.playwright.chromium.launch(
                headless=headless,
                args=browser_args
            )
            self.page = self.browser.new_page()
        except Exception as e:
            print(f"Failed to launch browser: {e}")
            print(f"Browser args: {browser_args}")
            print(f"Headless: {headless}")
            # Try to get more info about playwright installation
            import subprocess
            try:
                result = subprocess.run(["playwright", "install", "--help"], capture_output=True, text=True)
                print(f"Playwright available: yes")
            except:
                print(f"Playwright CLI not available")
            raise

    def login(self):
        """
        Login to Clubhouse Online

        Returns:
            bool: True if login successful, False otherwise
        """
        try:
            print(f"Navigating to {self.base_url}...")
            self.page.goto(self.base_url)

            # Wait for page to load
            time.sleep(2)

            # Find and fill username field
            print("Looking for login form...")
            username_selector = "#p_lt_page_content_pageplaceholder_p_lt_zoneLeft_CHOLogin_LoginControl_ctl00_Login1_UserName"
            self.page.locator(username_selector).wait_for(timeout=10000)
            self.page.locator(username_selector).clear()
            self.page.locator(username_selector).fill(self.username)
            print("✓ Username entered")

            # Find and fill password field
            password_selector = "#p_lt_page_content_pageplaceholder_p_lt_zoneLeft_CHOLogin_LoginControl_ctl00_Login1_Password"
            self.page.locator(password_selector).clear()
            self.page.locator(password_selector).fill(self.password)
            print("✓ Password entered")

            # Click login button
            login_button_selector = "#p_lt_page_content_pageplaceholder_p_lt_zoneLeft_CHOLogin_LoginControl_ctl00_Login1_LoginButton"
            self.page.locator(login_button_selector).click()
            print("✓ Login button clicked")

            # Wait for successful login
            time.sleep(3)

            # Check if login was successful
            if self.is_logged_in():
                print("✓ Login successful!")
                return True
            else:
                print("✗ Login failed - check credentials")
                return False

        except Exception as e:
            print(f"✗ Error during login: {str(e)}")
            return False

    def is_logged_in(self):
        """
        Check if user is logged in

        Returns:
            bool: True if logged in, False otherwise
        """
        try:
            # Check if logout link/button exists (typical indicator of logged-in state)
            logout_elements = self.page.get_by_text("Logout")
            if logout_elements.count() > 0:
                return True

            # Alternative: check page URL or other elements
            if "Member-Central" in self.page.url:
                return True

            return False
        except Exception as e:
            print(f"Error checking login status: {str(e)}")
            return False

    def navToTeeTimes(self):
        """
        Navigate to Tee Times page
        """
        try:
            print("Looking for tee time nav button...")
            tee_time_selector = "#p_lt_header_3_cmsmenu_menuElem-006"
            self.page.locator(tee_time_selector).wait_for(timeout=10000)
            self.page.locator(tee_time_selector).click()
            print("✓ Clicked Tee Times nav button")

            # Wait for tee times page to load - either URL change or container element
            try:
                self.page.wait_for_url("**/TeeTimes**", timeout=10000)
                print("✓ URL changed to TeeTimes page")
            except:
                # URL might not change, wait for the container instead
                print("  URL didn't change, waiting for page content...")
                self.page.locator("#modulesContainer").wait_for(timeout=10000)
                print("✓ Found modulesContainer element")

            # Additional wait for content to fully render
            time.sleep(2)

            if self.isOnTeeTimesPage():
                print("✓ Confirmed on Tee Times page")
                return True
            else:
                print("✗ Not on Tee Times page after navigation")
                print(f"  Current URL: {self.page.url}")
                return False
        except Exception as e:
            print(f"Error navigating to Tee Times page: {str(e)}")
            return False

    def isOnTeeTimesPage(self):
        """
        Check if currently on Tee Times page

        Returns:
            bool: True if on Tee Times page, False otherwise
        """
        try:
            # Check for specific element or URL indicative of Tee Times page
            if "TeeTimes" in self.page.url:
                return True

            tee_time_body = self.page.locator("#modulesContainer")
            if tee_time_body.count() > 0:
                return True

            return False
        except Exception as e:
            print(f"Error checking Tee Times page status: {str(e)}")
            return False

    def bookTeeTime(self, date, time_slot, players):
        """
        Book a tee time

        Args:
            date (str): Date for tee time (format: 'YYYY-MM-DD')
            time_slot (str): Desired time slot (e.g., '10:00 AM')
            players (list): List of player names

        Returns:
            bool: True if booking successful, False otherwise
        """
        try:
            print(f"Booking tee time on {date} at {time_slot} for players: {', '.join(players)}")
            # Implementation of booking logic goes here

            # Placeholder for success
            print("✓ Tee time booked successfully!")
            return True
        except Exception as e:
            print(f"Error booking tee time: {str(e)}")
            return False

    def find_date_element(self, day, month, year, click=False, timeout=10):
        """
        Find a calendar date element by its data attributes and optionally click it.

        Matches elements like:

        <a class="date-wrapper active" data-date="13" data-year="2025" data-month="12" ...>

        Args:
            day (int|str): Day number (e.g. 13)
            month (int|str): Month number (1-12)
            year (int|str): Full year (e.g. 2025)
            click (bool): If True, click the element after locating it
            timeout (int): Seconds to wait for the element to appear

        Returns:
            Playwright Locator or None
        """
        # Normalize to integers then strings to avoid leading-zero mismatches
        try:
            day_s = str(int(day))
            month_s = str(int(month))
            year_s = str(int(year))
        except Exception:
            day_s = str(day)
            month_s = str(month)
            year_s = str(year)

        selector = f"a.date-wrapper[data-date='{day_s}'][data-month='{month_s}'][data-year='{year_s}']"

        try:
            locator = self.page.locator(selector)
            locator.first.wait_for(timeout=timeout * 1000)

            if locator.count() == 0:
                return None

            # Get the first visible element
            target = locator.first

            if click:
                try:
                    # Scroll into view and click
                    target.scroll_into_view_if_needed()
                    target.click()
                except Exception:
                    # Fallback to JS click if normal click fails
                    try:
                        target.evaluate("el => el.click()")
                    except Exception as e:
                        print(f"Failed to click date element: {e}")
            return target
        except Exception as e:
            print(f"Error finding date element {day_s}-{month_s}-{year_s}: {e}")
            return None

    def select_tee_time(self, time_slot, hole, timeout=10):
        """
        Find and click on a specific tee time slot.

        Args:
            time_slot (str): Time slot to find (e.g., '8:07', '8:07 AM')
            hole (int|str): Hole number (e.g., 10 for 'Hole 10')
            timeout (int): Seconds to wait for elements to load

        Returns:
            bool: True if tee time was found and clicked, False otherwise
        """
        print(f"Looking for tee time: {time_slot} on Hole {hole}...")

        # Wait for tee times to load
        time.sleep(5)

        try:
            # Normalize time to HH:MM:SS format for data-timeof attribute
            # Handle AM/PM if explicitly provided
            is_pm = ' PM' in time_slot.upper() or ' pm' in time_slot.lower()
            is_am = ' AM' in time_slot.upper() or ' am' in time_slot.lower()

            time_normalized = time_slot.replace(' AM', '').replace(' PM', '').replace(' am', '').replace(' pm', '').strip()

            # Convert "8:07" to "08:07:00" or "1:30" to "13:30:00"
            parts = time_normalized.split(':')
            if len(parts) == 2:
                hour = int(parts[0])
                minute = parts[1].zfill(2)

                # If explicit AM/PM was provided, use that
                if is_pm and hour < 12:
                    hour += 12
                elif is_am and hour == 12:
                    hour = 0
                # If no AM/PM provided, infer from hour value
                # Golf tee times: hours 1-5 are typically PM (afternoon)
                # Hours 6-11 are AM, hour 12 is noon
                elif not is_pm and not is_am:
                    if 1 <= hour <= 5:
                        hour += 12  # 1:30 -> 13:30, 2:00 -> 14:00, etc.

                time_data = f"{str(hour).zfill(2)}:{minute}:00"
                print(f"  Time format: '{time_slot}' -> '{time_data}'")
            else:
                time_data = time_normalized

            # Build selector using data attributes
            # Structure: <div class="tt card" data-timeof="08:07:00" data-hole="10" data-slotsavailable="X">
            selector = f"div.tt.card[data-timeof='{time_data}'][data-hole='{hole}']"

            locator = self.page.locator(selector)

            if locator.count() == 0:
                print(f"✗ Could not find tee time element: {time_slot} on Hole {hole}")
                self._log_available_tee_times()
                return False

            element = locator.first

            # Check availability via data-slotsavailable attribute
            slots_available = element.get_attribute('data-slotsavailable')
            class_attr = element.get_attribute('class') or ''

            if slots_available == '0' or 'unavailable' in class_attr:
                print(f"✗ Tee time {time_slot} Hole {hole} is NOT AVAILABLE (slots: {slots_available})")

                # Try to get who booked it
                try:
                    player_names = element.locator('.player-name-text').all_inner_texts()
                    if player_names:
                        print(f"  Currently booked by: {', '.join(player_names)}")
                except Exception:
                    pass

                return False

            # Tee time is available - click the book button inside the card
            print(f"✓ Tee time {time_slot} Hole {hole} is AVAILABLE (slots: {slots_available})")
            element.scroll_into_view_if_needed()

            # Find and click the book button inside the card
            book_button = element.locator('button.book-btn')
            if book_button.count() > 0:
                book_button.first.click()
                print(f"✓ Clicked book button for: {time_slot} on Hole {hole}")
            else:
                # Fallback to clicking the card itself
                element.click()
                print(f"✓ Clicked on tee time card: {time_slot} on Hole {hole}")
            return True

        except Exception as e:
            print(f"✗ Error selecting tee time: {str(e)}")
            self._log_available_tee_times()
            return False

    def add_guests_to_booking(self, guest_name="Guest, TBD", num_guests=3, holes_to_play=18, transport="CART", timeout=10):
        """
        Add guests to the booking after selecting a tee time.

        This should be called after select_tee_time() opens the booking modal.

        Args:
            guest_name (str): Name to search for in the guest list
            num_guests (int): Number of guests to add (default 3, since player 1 is the member)
            holes_to_play (int): Number of holes to play (9 or 18)
            transport (str): Mode of transport - CART, WALK, or WALK/RIDE
            timeout (int): Seconds to wait for elements

        Returns:
            int: Number of guests successfully added
        """
        print(f"Adding {num_guests} guests to booking ({holes_to_play} holes, {transport})...")

        try:
            # Wait for booking modal to load
            time.sleep(4)

            # Click on Guests tab
            guests_tab = self.page.get_by_role("button", name="Guests")
            guests_tab.wait_for(timeout=timeout * 1000)
            guests_tab.click()
            print("✓ Clicked Guests tab")
            time.sleep(1)

            # Find and fill the search box
            search_box = self.page.get_by_role("searchbox", name="Search for Guest")
            search_box.wait_for(timeout=timeout * 1000)
            search_box.fill(guest_name)
            print(f"✓ Entered search term: {guest_name}")

            # Press Enter to search
            search_box.press("Enter")
            print("✓ Searching for guests...")
            time.sleep(2)  # Wait for search results

            # Click the "Add Player to your Group" buttons
            # Each button corresponds to a different guest in the search results
            guests_added = 0
            add_buttons = self.page.get_by_role("button", name="Add Player to your Group")
            button_count = add_buttons.count()
            print(f"  Found {button_count} 'Add Player' buttons")

            for i in range(min(num_guests, button_count)):
                try:
                    # Click the i-th button (0, 1, 2, ...)
                    add_buttons.nth(i).click()
                    guests_added += 1
                    print(f"✓ Added guest {guests_added}/{num_guests}")
                    time.sleep(0.5)  # Brief pause between clicks
                except Exception as e:
                    print(f"✗ Error adding guest {i+1}: {e}")
                    break

            print(f"✓ Added {guests_added} guests to the booking")

            # Select number of holes using "Define All > Holes" dropdown
            try:
                holes_button = self.page.get_by_role("button", name="Holes")
                holes_button.wait_for(timeout=timeout * 1000)
                holes_button.click()
                print("✓ Opened Holes dropdown")
                time.sleep(0.5)

                # Select 9 or 18 holes from the dropdown
                holes_option = self.page.get_by_role("link", name=str(holes_to_play))
                holes_option.click()
                print(f"✓ Selected {holes_to_play} holes")
                time.sleep(0.5)
            except Exception as e:
                print(f"⚠ Could not set holes (may already be set): {e}")

            # Select mode of transport using "Define All > MOT" button
            try:
                mot_button = self.page.get_by_role("button", name="MOT")
                mot_button.wait_for(timeout=timeout * 1000)
                mot_button.click()
                print("✓ Opened MOT dialog")
                time.sleep(0.5)

                # Map transport value to button text
                transport_map = {
                    "CART": "CART (CRT)",
                    "WALK": "WALK (WLK)",
                    "WALK/RIDE": "WALK/RIDE (W/R)"
                }
                transport_button_text = transport_map.get(transport.upper(), "CART (CRT)")

                # Click the transport option button
                transport_option = self.page.get_by_role("button", name=transport_button_text)
                transport_option.click()
                print(f"✓ Selected {transport} transport")
                time.sleep(0.5)
            except Exception as e:
                print(f"⚠ Could not set transport (may already be set): {e}")

            # Click Submit Reservation to confirm the booking
            # Note: This is a div element, not a button, containing "Submit" and "Reservation" text
            time.sleep(1)
            try:
                # Find the Submit element in the navigation bar
                modal_nav = self.page.locator("nav")
                submit_element = modal_nav.locator("text=Submit").first
                submit_element.wait_for(timeout=timeout * 1000)
                submit_element.click()
                print("✓ Clicked Submit Reservation")
                time.sleep(3)  # Wait for confirmation
            except Exception as e:
                print(f"✗ Error submitting reservation: {e}")
                # Try to go back on error
                try:
                    modal_nav = self.page.locator("nav:has-text('Submit')")
                    modal_nav.locator("text=Back").first.click()
                    time.sleep(3)
                except:
                    pass

            return guests_added

        except Exception as e:
            print(f"✗ Error adding guests: {str(e)}")
            # Try to go back even on error
            try:
                modal_nav = self.page.locator("nav:has-text('Submit')")
                modal_nav.locator("text=Back").first.click()
                time.sleep(3)
            except:
                pass
            return 0

    def _log_available_tee_times(self):
        """Debug helper to log visible tee time elements on the page."""
        try:
            print("\n  Debug: Attempting to find any tee time elements...")

            # Look for elements containing time patterns (e.g., "8:07", "10:30")
            # Search the entire page text for time patterns
            page_text = self.page.inner_text("body")
            import re
            time_pattern = re.findall(r'\d{1,2}:\d{2}(?:\s*[AP]M)?', page_text)
            if time_pattern:
                unique_times = list(dict.fromkeys(time_pattern))[:20]  # First 20 unique times
                print(f"  Found times on page: {', '.join(unique_times)}")

            # Look for elements with "8:07" specifically
            elements_with_time = self.page.locator("//*[contains(text(), '8:07')]")
            if elements_with_time.count() > 0:
                print(f"  Found {elements_with_time.count()} elements containing '8:07'")
                for i in range(min(elements_with_time.count(), 5)):
                    el = elements_with_time.nth(i)
                    tag = el.evaluate("el => el.tagName")
                    classes = el.get_attribute('class') or 'no-class'
                    print(f"    - <{tag}> class='{classes}'")

            # Save page HTML for debugging
            html_content = self.page.content()
            with open('/tmp/tee_times_page.html', 'w') as f:
                f.write(html_content)
            print("  Page HTML saved to /tmp/tee_times_page.html for inspection")

        except Exception as e:
            print(f"  Debug error: {e}")

    def get_page_content(self):
        """
        Get current page content

        Returns:
            str: Page HTML content
        """
        return self.page.content()

    def close(self):
        """Close the browser"""
        self.browser.close()
        self.playwright.stop()
        print("Browser closed")


def main():
    """Main function for bot usage"""
    import os
    from config_reader import get_config_from_sheets, get_default_config

    parser = argparse.ArgumentParser(description='Clubhouse Online Tee Time Bot')
    parser.add_argument('--keep-open', '-k', action='store_true',
                        help='Keep browser open after script finishes for manual navigation')
    parser.add_argument('--headless', action='store_true',
                        help='Run browser in headless mode (no GUI)')
    args = parser.parse_args()

    bot = None
    booked_times = []
    failed_times = []

    try:
        # Load configuration from Google Sheets
        sheet_id = os.environ.get('GOOGLE_SHEET_ID')
        if sheet_id:
            try:
                config = get_config_from_sheets(sheet_id)
                print(f"✓ Loaded config: book {config.tee_times_to_book} times, {len(config.preferences)} preferences")
            except Exception as e:
                print(f"⚠ Failed to load Google Sheets config: {e}. Using defaults.")
                config = get_default_config()
        else:
            print("⚠ No GOOGLE_SHEET_ID set, using default config")
            config = get_default_config()

        # Create bot instance
        bot = ClubhouseBot(headless=args.headless)

        # Perform login
        if bot.login():
            print("\n" + "="*50)
            print("Bot is logged in and ready for further actions")
            print("="*50)
            time.sleep(2)
        else:
            print("Failed to login")
            raise Exception("Login failed")

        if not bot.navToTeeTimes():
            print("Failed to navigate to Tee Times page.")
            raise Exception("Navigation to Tee Times failed")

        print("="*50)
        print("Successfully navigated to Tee Times page.")
        print("="*50)

        next_sat = get_next_saturday()

        if bot.find_date_element(next_sat.day, next_sat.month, next_sat.year, click=True) is None:
            print(f"✗ Could not find date element for {next_sat}")
            raise Exception(f"Could not find date element for {next_sat}")

        print("="*50)
        print(f"✓ Found and clicked on date element for {next_sat}")
        print("="*50)

        # Wait for tee times to load after date selection
        time.sleep(3)

        # Try to book tee times from preferences
        times_to_book = config.tee_times_to_book
        print(f"\nAttempting to book {times_to_book} tee times from {len(config.preferences)} preferences\n")

        for pref in config.preferences:
            if len(booked_times) >= times_to_book:
                print(f"✓ Reached target of {times_to_book} bookings, stopping")
                break

            print(f"Trying preference {pref.priority}: {pref.time} Hole {pref.hole} ({pref.holes_to_play} holes)")

            if bot.select_tee_time(pref.time, pref.hole):
                # Add guests to the booking and set holes to play
                guests_added = bot.add_guests_to_booking("Guest, TBD", num_guests=3, holes_to_play=pref.holes_to_play, transport=pref.transport)
                if guests_added > 0:
                    print(f"  ✓ Added {guests_added} guests to the booking ({pref.holes_to_play} holes, {pref.transport})")

                booked_times.append(pref)
                print(f"  ✓ Successfully selected: {pref.time} Hole {pref.hole}\n")
            else:
                failed_times.append(pref)
                print(f"  ✗ Not available: {pref.time} Hole {pref.hole}\n")

        # Summary
        print("="*50)
        print(f"SUMMARY: Booked {len(booked_times)}/{times_to_book} tee times")
        if booked_times:
            print("Booked:")
            for t in booked_times:
                print(f"  - {t.time} Hole {t.hole} ({t.holes_to_play} holes)")
        if failed_times:
            print("Unavailable:")
            for t in failed_times:
                print(f"  - {t.time} Hole {t.hole}")
        print("="*50)

        if args.keep_open:
            print("\n" + "="*50)
            print("Browser open. Press Enter to close...")
            print("="*50)
            input()
            if bot:
                bot.close()
        else:
            time.sleep(5)
            if bot:
                bot.close()

    except ValueError as e:
        print(f"Configuration Error: {e}")
        print("\nPlease set up your .env file with:")
        print("  CLUBHOUSE_USERNAME=your_username")
        print("  CLUBHOUSE_PASSWORD=your_password")
        if bot:
            if args.keep_open:
                print("\n" + "="*50)
                print("Browser open (error occurred). Press Enter to close...")
                print("="*50)
                input()
            bot.close()

    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        if bot:
            if args.keep_open:
                print("\n" + "="*50)
                print("Browser open (error occurred). Press Enter to close...")
                print("="*50)
                input()
            bot.close()


if __name__ == "__main__":
    main()
