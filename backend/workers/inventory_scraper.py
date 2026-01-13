"""
Inventory Collector (Phase 1)
Daily scraper using Selenium to build the course inventory from Purdue's schedule search.
"""

import re
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
import shutil
from selenium.webdriver.chrome.service import Service

def run_command_debug(cmd):
    import subprocess
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        print(f"CMD '{cmd}':\n{result.stdout}")
    except Exception as e:
        print(f"CMD '{cmd}' failed: {e}")

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from app.database import SessionLocal
from app.models import Course


class InventoryScraper:
    """Scrapes Purdue course schedule to build inventory"""

    BASE_URL = "https://selfservice.mypurdue.purdue.edu/prod/bwckschd.p_disp_dyn_sched"

    def __init__(self, headless: bool = True):
        """Initialize the scraper with Chrome driver"""
        self.driver = None
        self.headless = headless
        self.db = SessionLocal()


# ... (existing imports)


    def setup_driver(self):
        """Setup Chrome WebDriver with options"""
        import os
        print(f"DEBUG: PATH={os.environ.get('PATH')}")
        
        chrome_options = Options()
        
        # 1. Check strict CHROME_BIN environment variable (Highest Priority)
        chrome_bin = os.environ.get("CHROME_BIN")
        
        # 2. If not set, check common system paths
        if not chrome_bin:
            chrome_bins = ["chromium", "google-chrome", "google-chrome-stable", "chromium-browser"]
            for name in chrome_bins:
                path = shutil.which(name)
                if path:
                    chrome_bin = path
                    break
        
        if chrome_bin:
            print(f"Found Chrome binary at: {chrome_bin}")
            chrome_options.binary_location = chrome_bin
        else:
            print("WARNING: Could not find Chrome binary! Please set CHROME_BIN env var.")

        if self.headless:
            # Use new headless mode for better stability
            chrome_options.add_argument("--headless=new")
        
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        # 1. Check strict CHROMEDRIVER_PATH environment variable (Highest Priority)
        chromedriver_bin = os.environ.get("CHROMEDRIVER_PATH")
        
        # 2. If not set, check common names/paths
        if not chromedriver_bin:
            driver_bins = ["chromedriver", "chromium.chromedriver", "chromium-driver"]
            for name in driver_bins:
                path = shutil.which(name)
                if path:
                    chromedriver_bin = path
                    break
        
        service = None
        if chromedriver_bin:
            print(f"Found ChromeDriver binary at: {chromedriver_bin}")
            service = Service(executable_path=chromedriver_bin)
        else:
             print("WARNING: Could not find ChromeDriver binary! Selenium will try to download one.")

        try:
            if service:
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            else:
                self.driver = webdriver.Chrome(options=chrome_options)
        except Exception as e:
            print(f"Failed to initialize WebDriver: {e}")
            raise e
            
        self.driver.set_page_load_timeout(60)


    def extract_crn_from_title(self, title: str) -> Optional[str]:
        """
        Extract CRN from course title.
        Example: "Elementary Linear Algebra - 22126 - MA 35100 - 021"
        Returns: "22126"
        """
        # Pattern: course name - CRN (5 digits) - course code - section
        pattern = r'-\s*(\d{5})\s*-'
        match = re.search(pattern, title)
        return match.group(1) if match else None

    def extract_course_code(self, title: str) -> Optional[str]:
        """
        Extract course code from title.
        Example: "Elementary Linear Algebra - 22126 - MA 35100 - 021"
        Returns: "MA 35100"
        """
        # Pattern: subject + space + course number
        pattern = r'-\s*\d{5}\s*-\s*([A-Z]+\s+\d+)'
        match = re.search(pattern, title)
        return match.group(1) if match else None

    def extract_section_from_title(self, title: str) -> Optional[str]:
        """
        Extract section from course title.
        Example: "Elementary Linear Algebra - 22126 - MA 35100 - 021" returns "021"
        Example: "Systems Programming - 35151 - CS 25200 - L15" returns "L15"
        """
        # The section is usually the last part after the last dash
        # We can split by ' - ' and take the last element, but let's be safer
        # Format: Title - CRN - Code - Section
        parts = title.split(' - ')
        if len(parts) >= 4:
            return parts[-1].strip()
        return None

    def scrape_term_subjects(
        self,
        term_code: str,
        term_name: str,
        subjects: List[str],
        course_numbers: Optional[List[str]] = None
    ) -> int:
        """
        Scrape courses for a specific term and subjects.

        Args:
            term_code: Term code (e.g., "202620")
            term_name: Term name (e.g., "Spring 2026")
            subjects: List of subject codes (e.g., ["MA", "CS"])
            course_numbers: Optional list of specific course numbers (e.g., ["35100"])

        Returns:
            Number of courses scraped
        """
        total_courses = 0

        for subject in subjects:
            print(f"Scraping {subject} for {term_name}...")

            try:
                # Navigate to the schedule search page
                self.driver.get(self.BASE_URL)

                # Give the page time to fully load
                import time
                time.sleep(3)

                wait = WebDriverWait(self.driver, 30)  # Increased timeout to 30 seconds

                # Step 1: Select term using the correct selector
                print(f"  - Selecting term {term_code}...")
                term_select = Select(wait.until(
                    EC.presence_of_element_located((By.XPATH, "//select[@name='p_term']"))
                ))
                term_select.select_by_value(term_code)

                # Submit term selection
                submit_button = self.driver.find_element(By.XPATH, "//input[@type='submit' and @value='Submit']")
                submit_button.click()

                # Step 2: Wait for search form and select subject
                print(f"  - Waiting for search form...")
                wait.until(EC.presence_of_element_located((By.ID, "subj_id")))

                # Wait specifically for the target subject to be present in the options
                # This ensures the specific subject list has loaded for the selected term
                def subject_option_present(d):
                    try:
                        sel = Select(d.find_element(By.ID, "subj_id"))
                        for opt in sel.options:
                            if opt.get_attribute("value") == subject:
                                return True
                        return False
                    except:
                        return False
                wait.until(subject_option_present)

                print(f"  - Selecting subject {subject}...")
                subject_select = Select(self.driver.find_element(By.ID, "subj_id"))
                subject_select.select_by_value(subject)

                # If specific course numbers provided, enter them
                if course_numbers:
                    course_input = self.driver.find_element(By.ID, "crse_id")
                    course_input.clear()
                    # Enter courses separated by space
                    course_input.send_keys(" ".join(course_numbers))

                # Submit search - use the correct button value
                print(f"  - Submitting search...")
                submit_button = self.driver.find_element(
                    By.XPATH, "//input[@type='submit' and @value='Class Search']"
                )
                submit_button.click()

                # Wait for results
                print(f"  - Waiting for results...")
                wait.until(EC.presence_of_element_located((By.CLASS_NAME, "datadisplaytable")))

                # Parse the results
                print(f"  - Parsing results...")
                courses = self._parse_course_list(term_code, term_name)
                total_courses += len(courses)

                # Save to database
                self._save_courses(courses)

                print(f"  - Found {len(courses)} course sections")

            except TimeoutException as e:
                print(f"  - Timeout while scraping {subject}: {str(e)}")
                print(f"    Current URL: {self.driver.current_url}")
            except Exception as e:
                print(f"  - Error scraping {subject}: {str(e)}")
                import traceback
                traceback.print_exc()

        return total_courses

    def _parse_course_list(self, term_code: str, term_name: str) -> List[Dict]:
        """Parse the course list from the results page"""
        courses = []
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')

        # Find all course sections using the new structure
        # Course headers are in <th class="ddlabel">
        course_headers = soup.find_all('th', class_='ddlabel')

        for header in course_headers:
            try:
                # Extract title text from the link
                # Format: "{Title} - {CRN} - {SUBJ} {CRSE} - {SECTION}"
                title_link = header.find('a')
                if not title_link:
                    continue

                full_title = title_link.get_text(strip=True)

                # Extract CRN and course code using existing regex methods
                crn = self.extract_crn_from_title(full_title)
                course_code = self.extract_course_code(full_title)
                section = self.extract_section_from_title(full_title)

                if not crn or not course_code:
                    continue

                # Extract course name (first part before the first dash)
                course_name = full_title.split(' - ')[0].strip()

                # Find the meeting times table for this section
                # Look for table with caption "Scheduled Meeting Times"
                parent_row = header.find_parent('tr')
                if parent_row:
                    # Find the next row which contains meeting details
                    next_row = parent_row.find_next_sibling('tr')
                    if next_row:
                        # Find the meeting times table within the details
                        meeting_tables = next_row.find_all('table', class_='datadisplaytable')

                        instructor = "TBA"
                        time_info = "TBA"
                        days = "TBA"
                        schedule_type = "Lecture"

                        for table in meeting_tables:
                            caption = table.find('caption')
                            if caption and 'Scheduled Meeting Times' in caption.get_text():
                                # Found the meeting times table
                                # Get the first data row (skip header)
                                data_rows = table.find_all('tr')
                                for row in data_rows:
                                    cells = row.find_all('td', class_='dddefault')
                                    if len(cells) >= 7:
                                        # Columns: Type, Time, Days, Where, Date Range, Schedule Type, Instructors
                                        time_info = cells[1].get_text(strip=True)
                                        days = cells[2].get_text(strip=True)
                                        schedule_type = cells[5].get_text(strip=True)
                                        instructor = cells[6].get_text(strip=True)
                                        # Remove email links and (P) designation
                                        if instructor:
                                            instructor = instructor.split('(P)')[0].strip()
                                        break

                courses.append({
                    'crn': crn,
                    'course_code': course_code,
                    'title': course_name,
                    'section': section,
                    'instructor': instructor or "TBA",
                    'time': time_info or "TBA",
                    'days': days or "TBA",
                    'schedule_type': schedule_type or "Lecture",
                    'term_code': term_code,
                    'term_name': term_name,
                })

            except Exception as e:
                print(f"    - Error parsing course: {str(e)}")
                continue

        return courses

    def _save_courses(self, courses: List[Dict]):
        """Save or update courses in the database"""
        for course_data in courses:
            try:
                # Check if course exists
                existing_course = self.db.query(Course).filter(
                    Course.crn == course_data['crn']
                ).first()

                if existing_course:
                    # Update existing course
                    for key, value in course_data.items():
                        setattr(existing_course, key, value)
                else:
                    # Create new course
                    new_course = Course(**course_data)
                    self.db.add(new_course)

                self.db.commit()

            except Exception as e:
                print(f"    - Error saving course {course_data.get('crn')}: {str(e)}")
                self.db.rollback()

    def close(self):
        """Clean up resources"""
        if self.driver:
            self.driver.quit()
        if self.db:
            self.db.close()

    def __enter__(self):
        """Context manager entry"""
        self.setup_driver()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


def run_inventory_scraper(
    term_code: str = "202620",
    term_name: str = "Spring 2026",
    subjects: List[str] = None,
    headless: bool = True
):
    """
    Main function to run the inventory scraper.

    Args:
        term_code: Term code (e.g., "202620")
        term_name: Term name (e.g., "Spring 2026")
        subjects: List of subjects to scrape (e.g., ["MA", "CS", "ECON"])
        headless: Run browser in headless mode (default: True)
    """
    if subjects is None:
        # Default subjects - comprehensive list of popular departments
        subjects = [
            "MA", "CS", "ECON", "STAT", "PHYS", "CHEM",
            "BIOL", "ENGR", "MGMT", "ECE", "ME", "IE",
            "AAE", "ABE", "CHE", "CE", "MSE", "NE"
        ]

    print(f"Starting Inventory Scraper for {term_name} ({term_code})")
    print(f"Mode: {'Headless' if headless else 'Visible Browser'}")
    print(f"Subjects ({len(subjects)}): {', '.join(subjects)}")
    print("-" * 60)

    try:
        with InventoryScraper(headless=headless) as scraper:
            total = scraper.scrape_term_subjects(
                term_code=term_code,
                term_name=term_name,
                subjects=subjects
            )
            print("-" * 60)
            print(f"✅ Scraping complete! Total courses added/updated: {total}")
            return total

    except Exception as e:
        print(f"❌ Error running inventory scraper: {str(e)}")
        raise


if __name__ == "__main__":
    import sys

    # Check if user wants to run in visible mode (for debugging)
    visible_mode = "--visible" in sys.argv or "-v" in sys.argv

    if visible_mode:
        print("Starting scraper in VISIBLE browser mode (for debugging)...")
        print("You can watch the browser window to see what's happening.\n")
        headless = False
    else:
        print("Starting scraper in HEADLESS mode (production)...")
        headless = True

    # Default subjects to scrape - add/remove as needed
    subjects_to_scrape = [
        "MA",      # Mathematics
        "CS",      # Computer Science
        "ECON",    # Economics
        "STAT",    # Statistics
        "PHYS",    # Physics
        "CHEM",    # Chemistry
        "BIOL",    # Biology
        "ENGR",    # Engineering
        "MGMT",    # Management
        "ECE",     # Electrical & Computer Engineering
    ]

    with InventoryScraper(headless=headless) as scraper:
        total = scraper.scrape_term_subjects(
            term_code="202620",
            term_name="Spring 2026",
            subjects=subjects_to_scrape
        )
        print(f"\n{'='*60}")
        print(f"✅ Scraping complete!")
        print(f"Total courses scraped: {total}")
        print(f"{'='*60}")
