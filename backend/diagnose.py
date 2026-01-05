import os
import subprocess
import sys
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

def check_binary(name, path):
    print(f"--- Checking {name} at {path} ---")
    if not os.path.exists(path):
        print(f"❌ FAIL: File not found at {path}")
        return False
    
    # Try to execute it directly to check for missing libraries (e.g., libglib, libnss)
    try:
        result = subprocess.run([path, "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ SUCCESS: {name} is runnable. Version: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ FAIL: {name} returned error code {result.returncode}")
            print(f"Stderr: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ FAIL: Exception while running {name}: {e}")
        return False

# 1. Verify Binaries
# These paths match what we expect on Railway/Nixpacks
chrome_path = os.environ.get("CHROME_BIN", "/usr/bin/chromium")
driver_path = os.environ.get("CHROMEDRIVER_PATH", "/usr/bin/chromedriver")

bins_ok = check_binary("Chromium", chrome_path)
driver_ok = check_binary("ChromeDriver", driver_path)

if not (bins_ok and driver_ok):
    print("CRITICAL: Binaries are broken or missing. Check nixpacks.toml.")
    # Don't exit yet, try to list what's there
    try:
        print("\nListing /usr/bin to hunt for binaries:")
        subprocess.run("ls -F /usr/bin | grep chrom", shell=True)
    except:
        pass

# 2. Try Launching Selenium with Verbose Logging
print("\n--- Attempting to launch WebDriver ---")
try:
    options = Options()
    options.binary_location = chrome_path
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    
    # Enable verbose logging to stdout
    service = Service(executable_path=driver_path, log_output=sys.stdout)
    
    driver = webdriver.Chrome(service=service, options=options)
    print("✅ SUCCESS: WebDriver launched successfully!")
    driver.quit()
except Exception as e:
    print(f"❌ FAIL: Selenium crashed. Error:\n{e}")
