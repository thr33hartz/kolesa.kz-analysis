import os
import time
import random
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException # Added WebDriverException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urljoin 

START_URL = "https://kolesa.kz/cars/almaty/"
OUTPUT_CSV = "data/kolesa_almaty_found_urls.csv"
MAX_PAGES = 1

AD_LINK_SELECTOR = "a.a-card__link"
NEXT_PAGE_SELECTOR = "a.next_page" 
AD_LIST_CONTAINER_SELECTOR = "div.a-list" 

# setup
chrome_options = ChromeOptions()
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
# chrome_options.add_argument("--headless") # Run headless if you don't need to see the browser
chrome_options.add_argument("--window-size=1280,800")
user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
chrome_options.add_argument(f'user-agent={user_agent}')
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option('useAutomationExtension', False)

driver = None
all_urls = set()

# ensure data directory exists
os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)

# main script
try:
    print("Setting up WebDriver...")
    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    print("WebDriver setup complete.")

    current_url = START_URL
    page_count = 0

    while current_url and (MAX_PAGES is None or page_count < MAX_PAGES):
        page_count += 1
        print(f"Scraping page {page_count}: {current_url}")
        driver.get(current_url)
        time.sleep(random.uniform(3, 6)) # Wait for page to potentially load dynamic content

        try:
            # wait briefly for the ad list container to appear
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, AD_LIST_CONTAINER_SELECTOR))
            )
            time.sleep(random.uniform(1, 2)) # Extra small delay

            # find all ad links on the current page
            ad_elements = driver.find_elements(By.CSS_SELECTOR, AD_LINK_SELECTOR)
            found_on_page = 0
            for elem in ad_elements:
                href = elem.get_attribute('href')
                if href:
                    # ensure the URL is absolute
                    absolute_url = urljoin(START_URL, href) # Use urljoin here
                    if absolute_url.startswith('https://kolesa.kz/a/show/'): # Basic check if it looks like an ad URL
                       cleaned_url = absolute_url.split('?')[0] # Отсекаем все после '?'
                       all_urls.add(cleaned_url)
                       found_on_page += 1

            print(f"  Found {found_on_page} ad links on this page. Total unique URLs: {len(all_urls)}")

            # find and click the 'next page' button
            try:
                next_page_button = driver.find_element(By.CSS_SELECTOR, NEXT_PAGE_SELECTOR)
                # check if the button is disabled (some sites disable the last 'next' button)
                if next_page_button.is_enabled() and next_page_button.is_displayed():
                     next_page_href = next_page_button.get_attribute('href')
                     if next_page_href:
                         current_url = urljoin(current_url, next_page_href) # Make sure next url is absolute
                     else: # if href is missing or javascript based click needed
                         print("  Next page button found, but href is missing. Attempting click...")
                         next_page_button.click()
                         time.sleep(random.uniform(2,4))
                         current_url = driver.current_url
                         if current_url == driver.current_url:
                             print("  URL did not change after click, assuming end.")
                             current_url = None

                else:
                    print("  'Next page' button found but is disabled or not visible. Reached the end.")
                    current_url = None # Stop the loop

            except NoSuchElementException:
                print("  'Next page' button not found. Reached the end.")
                current_url = None # Stop the loop

        except TimeoutException:
            print(f"  Timeout waiting for ad list container '{AD_LIST_CONTAINER_SELECTOR}' on page {current_url}. Skipping page.")
            # decide whether to stop or try the next page if possible (here we stop)
            current_url = None
        except Exception as e:
            print(f"  An error occurred while processing page {current_url}: {e}")
            # decide whether to stop or continue
            # current_url = None # Option: Stop on error
            # option: try to find next page anyway? Risky. Best to stop here.
            current_url = None


except WebDriverException as e_wd:
    print(f"WebDriverException setting up or using WebDriver: {e_wd}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")
    import traceback # import traceback to print stack trace
    traceback.print_exc() # print stack trace for debugging
finally:
    if driver:
        print("Closing WebDriver.")
        driver.quit()

# save the collected URLs to a CSV file
if all_urls:
    print(f"\nFound a total of {len(all_urls)} unique URLs.")
    df_urls = pd.DataFrame(list(all_urls), columns=['url'])
    df_urls.to_csv(OUTPUT_CSV, index=False, encoding='utf-8')
    print(f"URLs saved to {OUTPUT_CSV}")
else:
    print("No URLs were collected.")

print("Script finished.")