# Almaty Car Market Analysis (kolesa.kz)

## Description

This project involves scraping, cleaning, analyzing, and visualizing car advertisement data from kolesa.kz, focusing on the Almaty car market.

### Objectives
- **Practice:** Enhance web scraping and data analysis skills.
- **Dataset Creation:** Build a dataset suitable for machine learning applications.

### Workflow
1. **Web Scraping:** Use Selenium and BeautifulSoup to extract advertisement URLs and detailed listing information.
2. **Data Cleaning:** Process raw data into a structured format using Pandas.
3. **Data Analysis:** Identify trends, patterns, and key statistics in the Almaty car market.
4. **Visualization:** Generate insightful plots and charts with Matplotlib and Seaborn.
5. **Future Plans:** Develop an interactive dashboard using Power BI.

## Technologies

### Programming Language
- **Python 3.x**

### Libraries and Tools
- **Web Scraping:**
    - `selenium`: Automate browser interactions.
    - `webdriver-manager`: Manage browser drivers.
    - `beautifulsoup4`: Parse HTML content.
- **Data Analysis:**
    - `pandas`: Data manipulation and analysis.
    - `numpy`: Perform numerical computations.
- **Visualization:**
    - `matplotlib`: Create static visualizations.
    - `seaborn`: Generate statistical plots.
- **Development Environment:**
    - `jupyterlab`: Interactive coding environment.
    - Virtual Environment (`venv`): Isolate project dependencies.

## Project Structure

```
kolesa.kz-analysis/
├── notebooks/                # Jupyter notebooks for analysis
│   └── cleaning-analysis.ipynb   # Notebook for EDA, cleaning and analysis
│
├── scripts/                  # Python scripts
│   ├── find_urls.py            # Script to scrape advertisement URLs from listing pages
│   └── web_scrapping.py        # Script to scrape detailed data using URLs from CSV
│
├── .gitignore                # Specifies intentionally untracked files (should include data/*.csv)
├── README.md                 # This file
└── requirements.txt          # Python package dependencies
```

## Data Description

The data for this project consists of information scraped from kolesa.kz car advertisements in Almaty.

**Note:** Due to their potential size, the CSV data files (`kolesa_almaty_found_urls.csv`, `kolesa_almaty_data.csv`, `kolesa_almaty_cleaned.csv`) are generally not included directly in this Git repository. The `.csv` files in the `data/` directory should be added to your `.gitignore`. Final or intermediate datasets might be available via an external link if provided.

**[Link to your Google Drive folder or specific files, if applicable]** <== **REPLACE OR REMOVE**

* **`kolesa_almaty_found_urls.csv`**: Contains a list of unique, cleaned advertisement URLs. This file is generated and updated by the `scripts/find_urls.py` script and serves as input for the detailed scraping process (`web_scrapping.py`).
    * `url`: Cleaned link to the advertisement (without query parameters).
* **`kolesa_almaty_data.csv`**: Contains raw detailed data scraped by `scripts/web_scrapping.py` for each URL from the `_found_urls.csv` file. This file is generated locally when running the scraper.
    * Columns: `brand`, `model`, `year`, `city`, `price`, `mileage`, `engine_volume_liters`, `body_style`, `color`, `transmission`, `drive_type`, `url`, `parsed_at`.
* **`kolesa_almaty_cleaned.csv`**: Contains cleaned and preprocessed data, ready for analysis and visualization. This is typically the output of the `cleaning-analysis.ipynb` notebook.
    * Columns are the same as `kolesa_almaty_data.csv`, but data types are corrected, and missing values are handled.
  
## Setup and Installation

1.  **Clone the repository:**
    ```bash
    git clone <your_repository_url>
    cd kolesa.kz-analysis
    ```
2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    # On Windows
    .\venv\Scripts\activate
    # On macOS/Linux
    source venv/bin/activate
    ```
3.  **Install the required dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *Note: Ensure you have Google Chrome installed, as the script uses `webdriver-manager` for Chrome.*

## Usage

The typical workflow involves running the scripts in order:

### 1. Find Advertisement URLs

Run the `scripts/find_urls.py` script to collect advertisement URLs from the kolesa.kz listing pages for Almaty.

* **Functionality:** This script navigates through the paginated results (up to `MAX_PAGES` defined in the script), extracts links to individual ads, cleans them (removes query parameters), and saves them to `data/kolesa_almaty_found_urls.csv`.
* **Behavior:** **Warning:** This script **overwrites** the `data/kolesa_almaty_found_urls.csv` file every time it runs successfully. It does *not* append to existing data or resume from previous runs.
* **Run the script:**
    ```bash
    python scripts/find_urls.py
    ```
* **Note:** You may need to verify/update the CSS selectors within the script (`AD_LINK_SELECTOR`, `NEXT_PAGE_SELECTOR`) if the website structure changes. Adjust `MAX_PAGES` in the script to control how many pages are scraped.

### 2. Scrape Detailed Data

Once you have populated `data/kolesa_almaty_found_urls.csv` (by running `find_urls.py`), run the `scripts/web_scrapping.py` script to scrape detailed information for each URL in that file.

* **Input:** Reads URLs from `data/kolesa_almaty_found_urls.csv`.
* **Output:** Saves detailed scraped data to `data/kolesa_almaty_data.csv`.
* **Run the scraper:**
    ```bash
    python scripts/web_scrapping.py
    ```
* **Configuration:** You can modify behavior within `web_scrapping.py`:
    * `run_update_mode = True`: (Default) Only scrapes URLs from the input file that are *not* already present in the output `_data.csv`. Set to `False` to re-scrape all URLs.
    * `max_ads_to_scrape = None`: (Default) No limit. Set to an integer to limit processing.