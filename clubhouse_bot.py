"""
Clubhouse Online Bot for Cypress Lake CC
Automates login to https://cypresslakecc.clubhouseonline-e3.com/Member-Central
"""

import os
import glob
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
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
        
        # Setup Chrome options
        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Initialize driver with proper chromedriver path
        try:
            # Try to get chromedriver path from webdriver-manager
            chromedriver_path = ChromeDriverManager().install()
            
            # Fix for macOS ARM64: find the actual executable if path points to a text file
            if not os.path.isfile(chromedriver_path) or chromedriver_path.endswith('.txt'):
                # Search for the actual chromedriver executable in the parent directory
                parent_dir = os.path.dirname(chromedriver_path)
                possible_paths = glob.glob(os.path.join(parent_dir, '**/chromedriver'), recursive=True)
                if possible_paths:
                    chromedriver_path = possible_paths[0]
                    print(f"Using chromedriver from: {chromedriver_path}")
            
            service = Service(chromedriver_path)
            self.driver = webdriver.Chrome(service=service, options=options)
        except Exception as e:
            print(f"Error initializing ChromeDriver: {e}")
            print("Trying with default Chrome...")
            self.driver = webdriver.Chrome(options=options)
        
        self.wait = WebDriverWait(self.driver, 10)
    
    def login(self):
        """
        Login to Clubhouse Online
        
        Returns:
            bool: True if login successful, False otherwise
        """
        try:
            print(f"Navigating to {self.base_url}...")
            self.driver.get(self.base_url)
            
            # Wait for page to load
            time.sleep(2)
            
            # Find and fill username field
            print("Looking for login form...")
            username_field = self.wait.until(
                EC.presence_of_element_located((By.ID, "p_lt_page_content_pageplaceholder_p_lt_zoneLeft_CHOLogin_LoginControl_ctl00_Login1_UserName"))
            )
            username_field.clear()
            username_field.send_keys(self.username)
            print("✓ Username entered")
            
            # Find and fill password field
            password_field = self.driver.find_element(By.ID, "p_lt_page_content_pageplaceholder_p_lt_zoneLeft_CHOLogin_LoginControl_ctl00_Login1_Password")
            password_field.clear()
            password_field.send_keys(self.password)
            print("✓ Password entered")
            
            # Click login button
            login_button = self.driver.find_element(By.ID, "p_lt_page_content_pageplaceholder_p_lt_zoneLeft_CHOLogin_LoginControl_ctl00_Login1_LoginButton")
            login_button.click()
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
            logout_elements = self.driver.find_elements(By.LINK_TEXT, "Logout")
            if logout_elements:
                return True
            
            # Alternative: check page URL or other elements
            if "Member-Central" in self.driver.current_url:
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
            tee_time_button = self.wait.until(
                EC.presence_of_element_located((By.ID, "p_lt_header_3_cmsmenu_menuElem-006"))
            )
            tee_time_button.click()
            print("✓ Navigated to Tee Times page")

            # Wait for tee times to load
            time.sleep(3)

            if self.isOnTeeTimesPage():
                print("✓ Confirmed on Tee Times page")
                return True
            else:
                print("✗ Not on Tee Times page after navigation")
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
            if "TeeTimes" in self.driver.current_url:
                return True
            
            tee_time_body = self.driver.find_elements(By.ID, "modulesContainer")
            if tee_time_body:
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
            selenium.webdriver.remote.webelement.WebElement or None
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
            elems = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector))
            )
            if not elems:
                return None

            # Prefer an element that is visible/clickable
            for el in elems:
                if el.is_displayed():
                    target = el
                    break
            else:
                target = elems[0]

            if click:
                try:
                    # scroll into view and click
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", target)
                    target.click()
                except Exception:
                    # fallback to JS click if normal click fails
                    try:
                        self.driver.execute_script("arguments[0].click();", target)
                    except Exception as e:
                        print(f"Failed to click date element: {e}")
            return target
        except Exception as e:
            print(f"Error finding date element {day_s}-{month_s}-{year_s}: {e}")
            return None
    
    def get_page_content(self):
        """
        Get current page content
        
        Returns:
            str: Page HTML content
        """
        return self.driver.page_source
    
    def close(self):
        """Close the browser"""
        self.driver.quit()
        print("Browser closed")


def main():
    """Main function for bot usage"""
    bot = None
    try:
        # Create bot instance
        bot = ClubhouseBot(headless=False)
        
        # Perform login
        if bot.login():
            print("\n" + "="*50)
            print("Bot is logged in and ready for further actions")
            print("="*50)
            
            # Keep browser open for 5 seconds to see the result
            time.sleep(5)
        else:
            print("Failed to login")

        if bot.navToTeeTimes():
            print("="*50)
            print("Successfully navigated to Tee Times page.")
            print("\n" + "="*50)
        else:
            print("Failed to navigate to Tee Times page.")

        next_sat = get_next_saturday()

        if bot.find_date_element(next_sat.day, next_sat.month, next_sat.year, click=True) != None:
            print("="*50)
            print(f"✓ Found and clicked on date element for {next_sat}")
            print("\n" + "="*50)
        else:
            print(f"✗ Could not find date element for {next_sat}")

        time.sleep(5)
    
    except ValueError as e:
        print(f"Configuration Error: {e}")
        print("\nPlease set up your .env file with:")
        print("  CLUBHOUSE_USERNAME=your_username")
        print("  CLUBHOUSE_PASSWORD=your_password")
    
    except Exception as e:
        print(f"Unexpected error: {e}")
    
    finally:
        if bot:
            bot.close()


if __name__ == "__main__":
    main()
