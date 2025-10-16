import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright, Error

# --- CONFIGURATION ---
DOMAINS_FILE = Path("screenshot_domains.txt")
# ---------------------

def take_screenshots():
    """
    Reads domains from a file, creates a dated directory,
    and saves a screenshot of each domain's website.
    """
    # 1. Set up the output directory
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    output_dir = Path(today_str)
    output_dir.mkdir(exist_ok=True)
    print(f"🖼️  Screenshots will be saved in: '{output_dir}/'")

    # 2. Read the list of domains
    if not DOMAINS_FILE.is_file():
        print(f"❌ Error: Input file '{DOMAINS_FILE}' not found.")
        # Create a sample file to help the user
        DOMAINS_FILE.write_text("google.com\n"
                                "github.com\n")
        print(f"A sample '{DOMAINS_FILE}' has been created. Please edit it and run the script again.")
        return

    with open(DOMAINS_FILE, "r") as f:
        # Read lines, strip whitespace, and ignore any empty lines
        domains = [line.strip() for line in f if line.strip()]

    if not domains:
        print("🤷 The domains.txt file is empty. Nothing to do.")
        return

    # 3. Launch the browser and take screenshots
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        
        print(f"\nFound {len(domains)} domains to process...")

        for domain in domains:
            # Ensure the domain has a protocol for the browser
            url = domain if domain.startswith(("http://", "https://")) else f"https://{domain}"
            
            print(f"   ↳ Processing {url}...")
            
            try:
                # Navigate to the page with a 20-second timeout
                page.goto(url, wait_until="domcontentloaded", timeout=20000)

                # Give the page a moment for any lazy-loaded elements to appear
                page.wait_for_timeout(2000)

                # Prepare filename as: DOMAIN_NAME_YYYY-MM-DD-HH-MM-SS.png
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
                safe_domain_name = domain.replace('.', '_').replace('/', '') # Sanitize for filename
                filename = f"{safe_domain_name}_{timestamp}.png"
                filepath = output_dir / filename

                # Take a full-page screenshot
                page.screenshot(path=filepath, full_page=True)
                print(f"     ✅ Saved screenshot to {filepath}")

            except Error as e:
                # Catch browser-related errors (e.g., timeout, navigation failed)
                print(f"     ❌ Failed to process {url}: {e.message.splitlines()[0]}")

        browser.close()

    print("\n✨ Script finished successfully!")

if __name__ == "__main__":
    take_screenshots()
