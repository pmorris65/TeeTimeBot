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
import glob

# Load environment variables
load_dotenv()

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
    """Main function to demonstrate bot usage"""
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
