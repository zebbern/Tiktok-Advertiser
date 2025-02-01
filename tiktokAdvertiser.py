import time
import json
import random
import os
import logging
import re
import sys
import argparse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options  # Adjust if using a different browser
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    TimeoutException,
    NoSuchElementException
)

# -------------------- Utility Functions -------------------- #
def remove_emojis(text):
    """Removes emojis from the given text."""
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # Emoticons
        "\U0001F300-\U0001F5FF"  # Symbols & Pictographs
        "\U0001F680-\U0001F6FF"  # Transport & Map Symbols
        "\U0001F1E0-\U0001F1FF"  # Flags
        "]+",
        flags=re.UNICODE
    )
    return emoji_pattern.sub(r'', text)

# -------------------- Logging Configuration -------------------- #
# Configure logging to output to both console and a log file
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

file_handler = logging.FileHandler("tiktok_bot.log", encoding='utf-8')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

logging.basicConfig(
    level=logging.INFO,
    handlers=[
        console_handler,
        file_handler
    ]
)
# -------------------- End Logging Configuration -------------------- #

class TikTokBot:
    def __init__(self, driver, comments, hashtags, login_email, login_password, cookies_file='tiktok_cookies.json', commented_file='commented_videos.json'):
        self.driver = driver
        self.comments = comments
        self.hashtags = hashtags
        self.login_email = login_email
        self.login_password = login_password
        self.cookies_file = cookies_file
        self.commented_file = commented_file
        self.commented_videos = self.load_commented_videos()

    def load_commented_videos(self):
        """Loads the list of commented videos from a JSON file."""
        if os.path.exists(self.commented_file):
            try:
                with open(self.commented_file, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                    logging.info(f"Loaded {len(data)} previously commented videos.")
                    return set(data)
            except json.JSONDecodeError:
                logging.error("Commented videos file contains invalid JSON. Starting fresh.")
                return set()
            except Exception as e:
                logging.error(f"Failed to load commented videos: {e}")
                return set()
        else:
            logging.info("No commented videos file found. Starting fresh.")
            return set()

    def save_commented_videos(self):
        """Saves the list of commented videos to a JSON file."""
        try:
            with open(self.commented_file, 'w', encoding='utf-8') as file:
                json.dump(list(self.commented_videos), file)
            logging.info("Commented videos have been saved successfully.")
        except Exception as e:
            logging.error(f"Failed to save commented videos: {e}")

    def save_cookies(self):
        """Saves cookies to a JSON file."""
        try:
            with open(self.cookies_file, 'w', encoding='utf-8') as file:
                json.dump(self.driver.get_cookies(), file)
            logging.info("Cookies have been saved successfully.")
        except Exception as e:
            logging.error(f"Failed to save cookies: {e}")

    def load_cookies(self):
        """Loads cookies from a JSON file if it exists and is valid."""
        if os.path.exists(self.cookies_file):
            try:
                with open(self.cookies_file, 'r', encoding='utf-8') as file:
                    cookies = json.load(file)
                    if not cookies:
                        logging.warning("Cookies file is empty. Skipping loading cookies.")
                        return False
                    for cookie in cookies:
                        # Adjust domain if necessary
                        if 'sameSite' in cookie:
                            if cookie['sameSite'] == 'None':
                                cookie['sameSite'] = 'Strict'  # Modify as per requirement
                        self.driver.add_cookie(cookie)
                logging.info("Cookies loaded successfully.")
                return True
            except json.JSONDecodeError:
                logging.error("Cookies file contains invalid JSON. Deleting the file and skipping cookies loading.")
                os.remove(self.cookies_file)
                return False
            except Exception as e:
                logging.error(f"An unexpected error occurred while loading cookies: {e}")
                return False
        logging.info("No cookies file found.")
        return False

    def close_popups(self):
        """Closes any pop-ups or overlays that might interfere with interactions."""
        try:
            # Example: Close a generic pop-up
            popup_close_button = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "close")]'))
            )
            popup_close_button.click()
            logging.info("Closed a pop-up successfully.")
            time.sleep(random.uniform(1, 2))
        except TimeoutException:
            # No pop-up found
            pass
        except Exception as e:
            logging.error(f"Failed to close a pop-up: {e}")

    def click_element(self, element, retries=3):
        """Attempts to click an element with retries."""
        for attempt in range(retries):
            try:
                element.click()
                logging.info("Clicked on element successfully.")
                return True
            except ElementClickInterceptedException:
                logging.warning(f"Attempt {attempt + 1} - Click intercepted. Retrying...")
                self.close_popups()
                time.sleep(random.uniform(1, 2))
        logging.error("Failed to click on element after multiple attempts.")
        return False

    def login(self):
        """Logs into TikTok using cookies if available, otherwise performs manual login."""
        self.driver.get("https://www.tiktok.com/login")
        if self.load_cookies():
            self.driver.refresh()
            time.sleep(random.uniform(3, 6))
            if "login" not in self.driver.current_url.lower():
                logging.info("Logged in using cookies.")
                return
            else:
                logging.warning("Cookies expired or invalid. Proceeding with manual login.")
        else:
            logging.info("No cookies found. Proceeding with manual login.")

        # Wait for login elements to load
        try:
            # Adjust selectors as per TikTok's current login flow
            email_input = WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.NAME, "email"))
            )
            password_input = self.driver.find_element(By.NAME, "password")
            login_button = self.driver.find_element(By.XPATH, '//button[@type="submit"]')

            email_input.clear()
            email_input.send_keys(self.login_email)
            logging.info("Entered email.")
            time.sleep(random.uniform(1, 2))
            password_input.clear()
            password_input.send_keys(self.login_password)
            logging.info("Entered password.")
            time.sleep(random.uniform(1, 2))
            if not self.click_element(login_button):
                raise Exception("Failed to click login button.")

            # Wait for login to complete by checking URL change or presence of a user avatar
            WebDriverWait(self.driver, 30).until(
                EC.url_changes("https://www.tiktok.com/login")
            )
            time.sleep(random.uniform(3, 5))  # Allow time for the page to fully load

            if "login" not in self.driver.current_url.lower():
                logging.info("Logged in successfully.")
                self.save_cookies()
            else:
                logging.warning("Login may not have been successful. Proceeding with manual login.")
                raise Exception("Login did not redirect as expected.")
        except Exception as e:
            logging.error(f"An error occurred during login: {e}")
            print("Please complete the login manually in the opened browser window.")
            input("Press Enter after completing login manually...")
            try:
                self.save_cookies()
                logging.info("Cookies saved after manual login.")
            except Exception as save_e:
                logging.error(f"Failed to save cookies after manual login: {save_e}")

    def post_comments_on_hashtags(self, max_comments_per_hashtag=3):
        """Navigates through specified hashtags and posts comments on videos."""
        for hashtag in self.hashtags:
            logging.info(f"Processing hashtag: #{hashtag}")
            hashtag_url = f"https://www.tiktok.com/tag/{hashtag}"
            self.driver.get(hashtag_url)
            time.sleep(random.uniform(5, 8))  # Allow page to load

            # Scroll to load enough videos
            for _ in range(3):  # Adjust the range for more scrolling
                self.driver.execute_script("window.scrollBy(0, 1000);")
                time.sleep(random.uniform(2, 4))

            # Find video links
            video_links = self.driver.find_elements(By.XPATH, '//a[@href and contains(@href, "/video/")]')
            video_links = list({link.get_attribute('href') for link in video_links})  # Remove duplicates

            logging.info(f"Found {len(video_links)} videos for #{hashtag}.")

            for video_url in video_links[:max_comments_per_hashtag]:
                if video_url in self.commented_videos:
                    logging.info(f"Already commented on {video_url}. Skipping...")
                    continue

                try:
                    self.driver.get(video_url)
                    time.sleep(random.uniform(5, 7))  # Allow video page to load

                    self.close_popups()

                    # Wait for comment box
                    comment_box = WebDriverWait(self.driver, 15).until(
                        EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"]'))
                    )

                    # Scroll to the comment box to ensure it's in view
                    self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", comment_box)
                    time.sleep(random.uniform(1, 2))

                    # Attempt to click the comment box
                    if not self.click_element(comment_box):
                        logging.error(f"Failed to click on comment box for {video_url}. Skipping...")
                        self.capture_screenshot("click_failed")
                        continue

                    # Select a random comment and remove emojis
                    original_comment = random.choice(self.comments)
                    comment = remove_emojis(original_comment)
                    logging.info(f"Selected comment: {comment}")

                    # Enter comment character by character
                    for char in comment:
                        comment_box.send_keys(char)
                        time.sleep(random.uniform(0.03, 0.07))  # Human-like typing speed

                    # Submit the comment
                    comment_box.send_keys(Keys.ENTER)
                    logging.info(f"Posted comment on {video_url}")
                    self.commented_videos.add(video_url)
                    self.save_commented_videos()
                    time.sleep(random.uniform(2, 5))  # Random delay between comments

                except TimeoutException:
                    logging.error(f"Timeout while trying to comment on {video_url}.")
                    self.capture_screenshot("timeout_error")
                    continue
                except ElementClickInterceptedException:
                    logging.error(f"Element click intercepted while trying to comment on {video_url}.")
                    self.capture_screenshot("click_intercepted_error")
                    continue
                except Exception as e:
                    logging.error(f"Failed to comment on {video_url}: {e}")
                    self.capture_screenshot("general_error")
                    continue

            time.sleep(random.uniform(10, 15))

    def capture_screenshot(self, error_type):
        """Captures a screenshot of the current browser window."""
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        screenshot_name = f"screenshot_{error_type}_{timestamp}.png"
        try:
            self.driver.save_screenshot(screenshot_name)
            logging.info(f"Captured screenshot: {screenshot_name}")
        except Exception as e:
            logging.error(f"Failed to capture screenshot: {e}")

    def follow_users_in_comments(self, max_follows=5):
        """Placeholder for potential future functionality to follow users."""
        pass

def parse_arguments():
    """Parses command-line arguments."""
    parser = argparse.ArgumentParser(description='TikTok Comment Bot Configuration')
    parser.add_argument('--hashtags', type=str, help='Path to custom hashtags file (one hashtag per line). If not provided, default hashtags will be used.')
    parser.add_argument('--comments', type=int, default=3, help='Number of comments per hashtag (default: 3)')
    return parser.parse_args()

def main():
    # -------------------- Configuration -------------------- #
    args = parse_arguments()

    EMAIL = "youremail@example.com"        # Replace with your TikTok email
    PASSWORD = "yourpassword"              # Replace with your TikTok password
    COOKIES_FILE = 'tiktok_cookies.json'
    COMMENTED_FILE = 'commented_videos.json'

    # Change to your own hashtags here for what your target group is
    DEFAULT_HASHTAGS = [
        'tech', 'security', 'github', 'projects',
        'cybersecurity', 'coding', 'programming', 'developers',
        'infosec', 'hacking', 'technews', 'technology',
        'devops', 'machinelearning', 'ai', 'artificialintelligence',
        'data', 'datascience', 'python', 'javascript',
        'software', 'opensource', 'ethicalhacking', 'networksecurity',
        'informationsecurity', 'pentesting', 'malware', 'cryptography',
        'itsecurity', 'securitytips', 'cyberthreats', 'firewalls',
        'cloudsecurity', 'dataprotection', 'ransomware', 'vulnerability',
        'securityawareness', 'securitybreach', 'securityresearch', 'incidentresponse'
    ]

    # Load hashtags from file or use default
    if args.hashtags:
        if os.path.exists(args.hashtags):
            try:
                with open(args.hashtags, 'r', encoding='utf-8') as file:
                    HASHTAGS = [line.strip().lstrip('#') for line in file if line.strip()]
                logging.info(f"Loaded {len(HASHTAGS)} hashtags from {args.hashtags}.")
            except Exception as e:
                logging.error(f"Failed to load hashtags from {args.hashtags}: {e}")
                HASHTAGS = DEFAULT_HASHTAGS
                logging.info("Falling back to default hashtags.")
        else:
            logging.error(f"Hashtags file {args.hashtags} does not exist. Using default hashtags.")
            HASHTAGS = DEFAULT_HASHTAGS
    else:
        HASHTAGS = DEFAULT_HASHTAGS
        logging.info("Using default hashtags.")

    # Comments list with GitHub reference
    COMMENTS = [
        "Love this! Check out my GitHub for cool projects: https://github.com/zebbern",
        "Interesting video! I share similar projects on GitHub: https://github.com/zebbern",
        "Great content! Feel free to explore my GitHub: https://github.com/zebbern",
        "Nice work! Visit my GitHub for more tech tools: https://github.com/zebbern",
        "Awesome! If you're into tech, check out my GitHub: https://github.com/zebbern",
        "Fantastic! I have related projects on GitHub: https://github.com/zebbern",
        "Great insights! Browse my GitHub repositories: https://github.com/zebbern",
        "Loved this! Explore my GitHub for more projects: https://github.com/zebbern",
        "Impressive! Check out my GitHub for similar tools: https://github.com/zebbern",
        "Excellent! Feel free to visit my GitHub: https://github.com/zebbern",
        "Nice video! I share security projects on GitHub: https://github.com/zebbern",
        "Great explanation! See my GitHub for related projects: https://github.com/zebbern",
        "Superb content! Explore my GitHub here: https://github.com/zebbern",
        "Loved your post! Visit my GitHub for tech tools: https://github.com/zebbern",
        "Excellent job! Check out my GitHub for more: https://github.com/zebbern",
        "Inspired by your video! Feel free to browse my GitHub: https://github.com/zebbern",
        "Great work! I have similar projects on GitHub: https://github.com/zebbern",
        "Awesome insights! Explore my GitHub projects: https://github.com/zebbern",
        "Fantastic video! Visit my GitHub for more tech content: https://github.com/zebbern",
        "Impressive! Check out my GitHub for tools: https://github.com/zebbern",
    ]

    MAX_COMMENTS_PER_HASHTAG = args.comments  # Number of comments per hashtag

    # -------------------- End Configuration -------------------- #

    # -------------------- Initialize Selenium WebDriver -------------------- #
    project_dir = os.path.dirname(os.path.abspath(__file__))
    cache_dir = os.path.join(project_dir, "selenium_cache")

    # Create the cache directory if it doesn't exist
    if not os.path.exists(cache_dir):
        try:
            os.makedirs(cache_dir)
            logging.info(f"Created custom Selenium cache directory at: {cache_dir}")
        except Exception as e:
            logging.error(f"Failed to create Selenium cache directory: {e}")
            print("Failed to create Selenium cache directory. Please check your permissions.")
            return

    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    # chrome_options.add_argument("--headless")  # Uncomment to run in headless mode
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")  # Reduce bot detection
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument(f"user-data-dir={cache_dir}")

    # Suppress ChromeDriver logs
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_argument("--disable-logging")
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])

    try:
        driver = webdriver.Chrome(options=chrome_options)
        logging.info("Initialized Chrome WebDriver successfully.")
    except Exception as e:
        logging.error(f"Failed to initialize Chrome WebDriver: {e}")
        print("Failed to initialize Chrome WebDriver. Ensure that ChromeDriver is installed and its path is set correctly.")
        return
    # -------------------- End Initialize Selenium WebDriver -------------------- #

    # -------------------- Initialize TikTokBot -------------------- #
    bot = TikTokBot(
        driver=driver,
        comments=COMMENTS,
        hashtags=HASHTAGS,
        login_email=EMAIL,
        login_password=PASSWORD,
        cookies_file=COOKIES_FILE,
        commented_file=COMMENTED_FILE
    )
    # -------------------- End Initialize TikTokBot -------------------- #

    try:
        bot.login()
        bot.post_comments_on_hashtags(max_comments_per_hashtag=MAX_COMMENTS_PER_HASHTAG)
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
    finally:
        logging.info("Bot execution finished. Closing browser in 10 seconds.")
        print("Bot execution finished. Closing browser in 10 seconds.")
        time.sleep(10)
        driver.quit()

if __name__ == "__main__":
    main()
