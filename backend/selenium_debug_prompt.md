# Debugging Selenium on Railway (Nixpacks)

I am trying to run a Python Selenium scraper (headless Chrome) on Railway, but it keeps crashing with exit code 127 (missing dependencies/binaries).

## Setup
*   **Platform:** Railway
*   **Builder:** Nixpacks
*   **Root Directory:** `/backend`
*   **Python Version:** 3.10 (pinned via `.python-version` and `nixpacks.toml`)

## Configuration Files

### `nixpacks.toml` (Located in `/backend/nixpacks.toml`)
```toml
[phases.setup]
nixPkgs = ["python310", "chromium", "chromedriver"]

[phases.install]
cmds = ["pip install -r requirements.txt"]

[start]
cmd = "uvicorn app.main:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips '*'"
```

### `inventory_scraper.py` (Driver Setup)
```python
def setup_driver(self):
    import shutil
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options

    chrome_options = Options()
    
    # Try to find system binary
    chrome_bins = ["chromium", "google-chrome", "google-chrome-stable", "chromium-browser"]
    for name in chrome_bins:
        path = shutil.which(name)
        if path:
            chrome_options.binary_location = path
            break

    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")

    # Try to find system driver
    driver_bins = ["chromedriver", "chromium.chromedriver", "chromium-driver"]
    service = None
    for name in driver_bins:
        path = shutil.which(name)
        if path:
            service = Service(executable_path=path)
            break
            
    if service:
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
    else:
        # Fallback to Selenium Manager (downloads driver)
        self.driver = webdriver.Chrome(options=chrome_options)
```

## The Error
When the worker runs, it fails to find the binaries in the PATH, falls back to the downloaded driver, and then crashes.

**Logs:**
```text
DEBUG: PATH=/app/.venv/bin:/app/.venv/bin:/mise/shims:/mise/shims:/mise/shims:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
WARNING: Could not find Chrome binary in PATH!
WARNING: Could not find ChromeDriver binary in PATH! Selenium will try to download one.
...
Error running inventory scraper: Message: Service /root/.cache/selenium/chromedriver/linux64/143.0.7499.169/chromedriver unexpectedly exited. Status code was: 127
```

## Questions
1.  Why are `chromium` and `chromedriver` not appearing in the `PATH` despite being listed in `nixpacks.toml`?
2.  Are the package names `chromium` and `chromedriver` correct for Nixpkgs?
3.  Do I need to check a specific location (like `/nix/store` or `/nix/var/nix/profiles/default/bin`) explicitly?
4.  Is there a better way to install Chrome/Chromium dependencies on Railway?
