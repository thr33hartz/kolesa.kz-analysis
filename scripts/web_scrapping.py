import os
import re
import time
import random
from datetime import datetime
import pandas as pd
from bs4 import BeautifulSoup
import traceback
from urllib.parse import urljoin

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException

# configuration for kolesa.kz
# main settings for parsing the site
KOLESA_ALMATY_CONFIG = {
    "site_name": "kolesa_almaty",
    "base_url": "https://kolesa.kz",  # base url for joining relative links
    "input_urls_csv_template": "{site_name}_found_urls.csv",  # input file template
    "output_data_csv_template": "{site_name}_data.csv",  # output file template
    "columns": [  # output csv structure
        'brand', 'model', 'year', 'city', 'price', 'mileage',
        'engine_volume_liters', 'body_style', 'color', 'transmission',
        'drive_type', 'url', 'parsed_at'
    ],
    "wait_timeout": 10,  # increased timeout
    "wait_for_selector": "div.offer__price",  # element to wait for on the ad page
    "url_prefix_needed": True,  # whether to add prefix to relative urls

    # selectors and parsing rules
    # maps column names to data extraction methods
    "selectors": {
        'brand': {'selector': 'span[itemprop="brand"]', 'type': 'text'},
        'model': {'selector': 'span[itemprop="name"]', 'type': 'text'},
        'year': {'selector': 'span.year', 'type': 'numeric'},
        'price': {'selector': 'div.offer__price', 'type': 'numeric'},
        'city_alt': {'selector': 'div.offer__location', 'type': 'text'},  # alternative selector for city

        # special handler for the details block
        'details_block': {
            'block_selector': 'div.offer__parameters dl',  # selector for each parameter (dt+dd)
            'key_selector': 'dt.value-title',  # selector for parameter name
            'value_selector': 'dd.value',  # selector for parameter value
            'mapping': {  # maps text in 'key_selector' to columns and types
                'Город': {'column': 'city', 'type': 'text'},
                'Кузов': {'column': 'body_style', 'type': 'text'},
                'Объем двигателя, л': {'column': 'engine_volume_liters', 'type': 'float'},
                'Пробег': {'column': 'mileage', 'type': 'numeric'},
                'Коробка передач': {'column': 'transmission', 'type': 'text'},
                'Цвет': {'column': 'color', 'type': 'text'},
                'Привод': {'column': 'drive_type', 'type': 'text'}
            }
        }
        # add more selectors or handlers for other sites
    },
    "essential_fields": ['brand', 'price']  # fields that must be filled to save data
}

# utilities
def init_csv(path, columns):
    # creates csv file with headers if it doesn't exist or is empty
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        print(f"creating/resetting csv with header: {path}")
        pd.DataFrame(columns=columns).to_csv(path, index=False, encoding='utf-8')

def save_to_csv(data: dict, path, columns):
    # appends a row of data to the csv file
    try:
        # saves only specified columns in the correct order
        data_to_save = {col: data.get(col) for col in columns}
        df_to_save = pd.DataFrame([data_to_save], columns=columns)
        
        file_exists = os.path.exists(path)
        header = not file_exists or os.path.getsize(path) == 0
        
        df_to_save.to_csv(path, mode='a', header=header, index=False, encoding='utf-8')
    except Exception as e:
        print(f"error saving data to {path}: {e}")
        print(f"data attempted to save: {data}")  # log problematic data

def clean_text(text):
    # removes extra spaces from text
    return ' '.join(text.split()) if text else None

def extract_numeric(text):
    # extracts numeric value from text
    if not text: return None
    digits = re.findall(r'\d+', str(text))
    return int("".join(digits)) if digits else None

def extract_float(text):
    # extracts floating-point number from text
    if not text: return None
    match = re.search(r'(\d[\d\s]*[.,]?\d*)', str(text).replace(' ', '')) 
    if match:
        try:
            return float(match.group(1).replace(',', '.'))
        except ValueError:
            return None
    return None

# parsing html
def parse_html_details(page_source, url, config):
    # parses html page using beautifulsoup based on configuration
    extracted_data = {}
    try:
        soup = BeautifulSoup(page_source, 'lxml')
        extracted_data['url'] = url
        extracted_data['parsed_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        selectors_config = config.get('selectors', {})

        for column, rule in selectors_config.items():
            if column == 'details_block':  # processing the details block
                block_config = rule
                details_map = block_config.get('mapping', {})
                param_blocks = soup.select(block_config.get('block_selector', ''))

                for block in param_blocks:
                    key_element = block.select_one(block_config.get('key_selector', ''))
                    value_element = block.select_one(block_config.get('value_selector', ''))

                    if key_element and value_element:
                        key_text = clean_text(key_element.text)
                        value_text = clean_text(value_element.text)

                        if key_text in details_map:
                            target_info = details_map[key_text]
                            target_column = target_info.get('column') if isinstance(target_info, dict) else target_info
                            target_type = target_info.get('type', 'text') if isinstance(target_info, dict) else 'text'

                            if target_column:
                                if target_type == 'numeric':
                                    extracted_data[target_column] = extract_numeric(value_text)
                                elif target_type == 'float':
                                    extracted_data[target_column] = extract_float(value_text)
                                else:
                                    extracted_data[target_column] = value_text
            
            elif isinstance(rule, dict):  # processing rules based on dictionary (selector + type)
                selector = rule.get('selector')
                data_type = rule.get('type', 'text')
                element = soup.select_one(selector) if selector else None
                 
                if element:
                    raw_text = clean_text(element.text)
                    if data_type == 'numeric':
                        extracted_data[column] = extract_numeric(raw_text)
                    elif data_type == 'float':
                        extracted_data[column] = extract_float(raw_text)
                    else:
                        extracted_data[column] = raw_text
            
            elif isinstance(rule, str):  # processing simple string rules (default text)
                selector = rule
                element = soup.select_one(selector) if selector else None
                if element:
                    extracted_data[column] = clean_text(element.text)

        # fallback logic for city
        if 'city' not in extracted_data or not extracted_data['city']:
            if 'city_alt' in selectors_config and 'city_alt' in extracted_data:
                extracted_data['city'] = extracted_data.pop('city_alt', None)

        # returns only columns defined in the configuration
        final_data = {col: extracted_data.get(col) for col in config['columns']}
        return final_data

    except Exception as e:
        print(f"error parsing details with bs4 for {url}: {e}")
        traceback.print_exc()
        return {col: None for col in config['columns']}

# main parsing logic
def run_selenium_parser_from_file(config, max_ads=None, update=True):
    # runs the parser using selenium and a list of urls from a file
    site_name = config['site_name']
    input_path = config['input_urls_csv_template'].format(site_name=site_name)
    data_path = config['output_data_csv_template'].format(site_name=site_name)
    columns = config['columns']
    base_url = config.get('base_url')
    url_prefix_needed = config.get('url_prefix_needed', False)
    wait_timeout = config.get('wait_timeout', 10)
    wait_selector = config.get('wait_for_selector')
    essential_fields = config.get('essential_fields', [])

    init_csv(data_path, columns)

    print(f"--- loading urls from {input_path} ---")
    try:
        urls_to_parse_df = pd.read_csv(input_path, dtype={'url': str})
        if urls_to_parse_df.empty or 'url' not in urls_to_parse_df.columns:
            print(f"url file '{input_path}' is empty or missing 'url' column. exiting.")
            return
        
        if url_prefix_needed and base_url:
            print(f"prepending base url '{base_url}' to relative urls...")
            urls_to_parse_df['url'] = urls_to_parse_df['url'].apply(
                lambda x: x if str(x).startswith('http') else urljoin(base_url, str(x))
            )

        urls_to_parse_df.drop_duplicates(subset=['url'], inplace=True)
        print(f"loaded {len(urls_to_parse_df)} unique urls.")
    except FileNotFoundError:
        print(f"input url file '{input_path}' not found. cannot parse details.")
        return
    except Exception as e:
        print(f"error loading urls from {input_path}: {e}")
        return

    if update:
        print("update mode on: filtering out already parsed urls...")
        try:
            existing_data_df = pd.read_csv(data_path, dtype={'url': str}, usecols=['url'])
            if not existing_data_df.empty:
                parsed_urls = set(existing_data_df['url'].astype(str))
                print(f"found {len(parsed_urls)} previously parsed urls in {data_path}")
                original_count = len(urls_to_parse_df)
                urls_to_parse_df = urls_to_parse_df[~urls_to_parse_df['url'].isin(parsed_urls)].copy()
                print(f"urls remaining to parse after filtering: {len(urls_to_parse_df)} (filtered out {original_count - len(urls_to_parse_df)})")
            else:
                print(f"output file '{data_path}' exists but is empty or has no urls. no filtering applied.")
        except FileNotFoundError:
            print(f"output file '{data_path}' not found for update check. no filtering applied.")
        except Exception as e:
            print(f"error loading or processing previously parsed data from {data_path} for update check: {e}")
            print("proceeding without filtering (potential duplicates).")

    if urls_to_parse_df.empty:
        print("no new urls to parse. exiting.")
        return

    urls_to_parse = urls_to_parse_df['url'].tolist()

    if max_ads is not None and len(urls_to_parse) > max_ads:
        print(f"limiting parsing to first {max_ads} ads from the remaining list.")
        urls_to_parse = urls_to_parse[:max_ads]

    chrome_options = ChromeOptions()
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1280,800")
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
    chrome_options.add_argument(f'user-agent={user_agent}')
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    driver = None
    print("setting up webdriver...")
    try:
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        print("webdriver setup complete.")
    except WebDriverException as e_wd:
        print(f"webdriverexception setting up webdriver: {e_wd}")
        print("this might be due to chromedriver issues (version mismatch, permissions) or chrome browser problems.")
        return
    except Exception as e:
        print(f"error setting up webdriver: {e}")
        return

    print(f"\n--- starting detail parsing phase for {len(urls_to_parse)} urls (selenium) ---")
    parsed_count = 0
    failed_count = 0
    skipped_count = 0

    for i, ad_url in enumerate(urls_to_parse):
        print(f"parsing ad {i+1}/{len(urls_to_parse)}: {ad_url}")
        extracted_data = None
        try:
            time.sleep(random.uniform(1.5, 4.0))
            
            driver.get(ad_url)

            if wait_selector:
                WebDriverWait(driver, wait_timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, wait_selector))
                )
            else:
                time.sleep(random.uniform(1.0, 2.0))

            time.sleep(random.uniform(0.4, 1.0))

            ad_page_source = driver.page_source

            extracted_data = parse_html_details(ad_page_source, ad_url, config)

            is_essential_data_present = all(extracted_data.get(field) for field in essential_fields)

            if extracted_data and is_essential_data_present:
                save_to_csv(extracted_data, data_path, columns)
                parsed_count += 1
                print(f"  success: saved data for {ad_url}")
            elif not is_essential_data_present:
                print(f"  skipping save: essential data missing ({', '.join(essential_fields)}) for {ad_url}")
                print(f"  extracted: { {k: v for k, v in extracted_data.items() if k in essential_fields} }")
                skipped_count += 1
            else:
                print(f"  skipping save: parsing function failed significantly for {ad_url}")
                failed_count += 1

        except TimeoutException:
            print(f"  timeout waiting for element '{wait_selector}' on ad page: {ad_url}")
            failed_count += 1
        except WebDriverException as e_wd:
            print(f"  webdriverexception during processing {ad_url}: {e_wd}")
            failed_count += 1
        except Exception as e:
            print(f"  error processing ad {ad_url}: {type(e).__name__} - {e}")
            traceback.print_exc()
            failed_count += 1

    if driver:
        print("\nclosing webdriver.")
        driver.quit()
        
    print("\n--- scraping process finished ---")
    print(f"successfully parsed and saved: {parsed_count}")
    print(f"skipped (missing essential data): {skipped_count}")
    print(f"failed (errors or timeouts): {failed_count}")
    print(f"data saved to: {data_path}")

if __name__ == "__main__":
    ACTIVE_CONFIG = KOLESA_ALMATY_CONFIG
    run_update_mode = True # true for update mode, false for full scrape
    # set to None for no limit, or specify a number for maximum ads to scrape
    max_ads_to_scrape = None

    start_time = time.time()
    print(f"script started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"using configuration for: {ACTIVE_CONFIG['site_name']}")
    print(f"mode: parsing details from existing url file.")
    if run_update_mode: print("update filtering is on.")
    else: print("update filtering is off (will re-parse all urls in file).")
    if max_ads_to_scrape: print(f"maximum ads to scrape limit: {max_ads_to_scrape}")

    try:
        run_selenium_parser_from_file(
            config=ACTIVE_CONFIG,
            max_ads=max_ads_to_scrape,
            update=run_update_mode
        )
    except KeyboardInterrupt:
        print("\nscript interrupted by user (ctrl+c).")
    except Exception as main_e:
        print(f"\nan unexpected error occurred in the main execution block: {main_e}")
        traceback.print_exc()
    finally:
        end_time = time.time()
        print(f"\nscript finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"total execution time: {end_time - start_time:.2f} seconds")