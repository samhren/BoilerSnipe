"""
Debug Scraper with HTML Dumping
"""

import sys
import os
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# We don't need the DB for this debug script, so we'll mock or skip DB parts
class DebugScraper:
    BASE_URL = "https://selfservice.mypurdue.purdue.edu/prod/bwckschd.p_disp_dyn_sched"

    def __init__(self):
        chrome_options = Options()
        # Run HEADLESS for now unless we really need to see it, but user asked for "test it out get the html per step"
        # stick to headless to make it run on server easily, or we can make it visible if user runs locally. 
        # I'll keep it headless for the tool execution.
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.set_page_load_timeout(60)

    def save_html(self, filename):
        with open(filename, "w", encoding="utf-8") as f:
            f.write(self.driver.page_source)
        print(f"saved {filename}")

    def run(self):
        term_code = "202620" # Spring 2026
        subject = "CS"

        print(f"Debugging scraper for {subject} in {term_code}...")

        try:
            # 1. Load Page
            print("1. Loading page...")
            self.driver.get(self.BASE_URL)
            time.sleep(3)
            self.save_html("debug_1_initial_load.html")

            wait = WebDriverWait(self.driver, 30)

            # 2. Select Term
            print("2. Selecting term...")
            
            # DEBUG: Try finding by name first to see if element is accessible
            try:
                print("  - Attempting find by NAME 'p_term'...")
                elem = self.driver.find_element(By.NAME, "p_term")
                print(f"  - Found by NAME! ID: '{elem.get_attribute('id')}' Tag: '{elem.tag_name}'")
            except Exception as e:
                print(f"  - Failed find by NAME: {e}")

            # DEBUG: Try finding by ID directly without wait
            try:
                print("  - Attempting find by ID 'term_input_id' (no wait)...")
                elem = self.driver.find_element(By.ID, "term_input_id")
                print(f"  - Found by ID! Tag: '{elem.tag_name}'")
            except Exception as e:
                print(f"  - Failed find by ID: {e}")

            try:
                # Use a generic presence wait first
                print("  - Waiting for presence of select element...")
                term_select_elem = wait.until(
                    EC.presence_of_element_located((By.XPATH, "//select[@name='p_term']"))
                )
                print("  - Element found via XPath wait.")
                
                term_select = Select(term_select_elem)
                term_select.select_by_value(term_code)
                print("  - Selected term successfully.")
                self.save_html("debug_2_term_selected.html")
            except Exception as e:
                print(f"Failed at term selection (Main Attempt): {e}")
                self.save_html("debug_error_term_select.html")
                return

            # 3. Submit Term
            print("3. Submitting term...")
            try:
                submit_button = self.driver.find_element(By.XPATH, "//input[@type='submit' and @value='Submit']")
                submit_button.click()
                time.sleep(2) # Wait for reload
                self.save_html("debug_3_term_submitted.html")
            except Exception as e:
                print(f"Failed at term submit: {e}")
                self.save_html("debug_error_term_submit.html")
                return

            # 4. Select Subject
            print("4. Selecting subject...")
            try:
                wait.until(EC.presence_of_element_located((By.ID, "subj_id")))
                subject_select = Select(self.driver.find_element(By.ID, "subj_id"))
                subject_select.select_by_value(subject)
                self.save_html("debug_4_subject_selected.html")
            except Exception as e:
                print(f"Failed at subject selection: {e}")
                self.save_html("debug_error_subject_select.html")
                return

            # 5. Submit Search
            print("5. Submitting search...")
            try:
                submit_button = self.driver.find_element(
                    By.XPATH, "//input[@type='submit' and @value='Class Search']"
                )
                submit_button.click()
                self.save_html("debug_5_search_submitted.html")
            except Exception as e:
                print(f"Failed at search submit: {e}")
                self.save_html("debug_error_search_submit.html")
                return

            # 6. Wait for Results
            print("6. Waiting for results...")
            try:
                wait.until(EC.presence_of_element_located((By.CLASS_NAME, "datadisplaytable")))
                self.save_html("debug_6_results_loaded.html")
                print("Success! Results loaded.")
            except Exception as e:
                print(f"Failed waiting for results: {e}")
                self.save_html("debug_error_results_wait.html")

        except Exception as e:
            print(f"Global error: {e}")
        finally:
            self.driver.quit()

if __name__ == "__main__":
    scraper = DebugScraper()
    scraper.run()
