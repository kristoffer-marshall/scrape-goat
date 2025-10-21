import requests
import os
import random
import argparse
import re
import csv
import urllib3
from urllib.parse import urlparse, unquote
from bs4 import BeautifulSoup
from datetime import datetime
import colorama
from colorama import Fore, Style
import configparser
import concurrent.futures
from threading import Lock

# --- Configuration ---
CONFIG_FILE = 'config.ini'
LOGS_DIR = 'logs'
LISTS_DIR = 'domain-lists'
MATCHES_FILE = os.path.join(LOGS_DIR, 'matches.log')
NO_MATCHES_FILE = os.path.join(LOGS_DIR, 'no_matches.log')
ERRORS_FILE = os.path.join(LOGS_DIR, 'errors.log')

# --- Globals for thread safety ---
print_lock = Lock()
file_lock = Lock()
scanned_base_domains = set()
sites_with_hits = 0
scanned_count = 0

def load_config(config_filename):
    """Parses the INI configuration file."""
    config = configparser.ConfigParser()
    if not os.path.exists(config_filename):
        return None
    config.read(config_filename)
    return config

def get_default_list_name(config):
    """Finds the list marked as default in the config."""
    for section in config.sections():
        if config.has_option(section, 'default') and config.getboolean(section, 'default'):
            return section
    if config.sections():
        return config.sections()[0]
    return None

def count_csv_entries(filename):
    """Counts the number of data rows in a CSV file, skipping the header."""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)
            return sum(1 for row in reader if row)
    except (FileNotFoundError, StopIteration, csv.Error):
        return 0

def update_domain_list(filename, url):
    """Downloads the latest domain list and reports changes in entry count."""
    with print_lock:
        print(f"-> Checking for domain list updates from {url}...")
    
    original_entry_count = count_csv_entries(filename)
    if original_entry_count > 0:
        with print_lock:
            print(f"-> Existing file '{filename}' contains {original_entry_count} entries.")

    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        
        with open(filename, 'w', encoding='utf-8', newline='') as f:
            f.write(response.text)
        
        with print_lock:
            print(f"-> Successfully downloaded and saved the list to {filename}.")
        
        new_entry_count = count_csv_entries(filename)
        
        with print_lock:
            if original_entry_count > 0:
                change = new_entry_count - original_entry_count
                if change > 0:
                    print(f"-> {change} entries were added to the list (new total: {new_entry_count}).")
                elif change < 0:
                    print(f"-> {abs(change)} entries were removed from the list (new total: {new_entry_count}).")
                else:
                    print(f"-> The number of entries remains the same ({new_entry_count}).")
            else:
                print(f"-> The new list contains {new_entry_count} entries.")
        return True
    except requests.exceptions.RequestException as e:
        with print_lock:
            print(f"{Fore.RED}[ERROR] Could not download the list: {e}")
        return False

def get_base_domain(url):
    """Extracts the base domain (e.g., 'example.gov') from a full URL."""
    try:
        netloc = urlparse(url).netloc
        parts = netloc.split('.')
        if len(parts) > 2 and parts[-2] in ('co', 'com', 'org', 'net', 'gov', 'ac', 'edu'):
             return f"{parts[-3]}.{parts[-2]}.{parts[-1]}"
        elif len(parts) > 1:
            return f"{parts[-2]}.{parts[-1]}"
        return netloc
    except:
        return None

def load_domains_from_csv(filename):
    """Reads domains from the first column of a CSV file, skipping the header."""
    domains = []
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader)
            with print_lock:
                print(f"-> Reading domains from CSV '{filename}' (using column '{header[0]}').")
            for row in reader:
                if row:
                    domain = row[0].strip().lower()
                    if domain:
                        domains.append(domain)
        return domains
    except Exception as e:
        with print_lock:
            print(f"Error reading CSV {filename}: {e}")
        return None

def read_file_lines(filename):
    """Reads lines from a simple text file and returns them as a list."""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        with print_lock:
            print(f"{Fore.RED}Error: {filename} not found.")
        return None

def load_domains(filename):
    """Loads domains from a file, auto-detecting .csv or .txt format."""
    if not os.path.exists(filename):
        with print_lock:
            print(f"{Fore.RED}Error: Input file '{filename}' not found after check.")
        return None
        
    if filename.lower().endswith('.csv'):
        return load_domains_from_csv(filename)
    elif filename.lower().endswith('.txt'):
        with print_lock:
            print(f"-> Reading domains from text file '{filename}'.")
        return read_file_lines(filename)
    else:
        with print_lock:
            print(f"{Fore.RED}Error: Unsupported file format for '{filename}'. Please use a .csv or .txt file.")
        return None

def parse_keywords(keyword_string):
    """Parses a comma-separated string of keywords, respecting quotes."""
    return [kw.strip() for kw in csv.reader([keyword_string], skipinitialspace=True).__next__()]

def get_response(url):
    """Attempts to get a response from a URL, handling SSL errors."""
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'}
    ssl_note = None
    try:
        response = requests.get(url, headers=headers, timeout=10, verify=True, allow_redirects=True)
        response.raise_for_status()
        return response, None, None
    except requests.exceptions.SSLError as e:
        ssl_note = f"SSL verification failed ({e}), but proceeding with the scan."
        try:
            response = requests.get(url, headers=headers, timeout=10, verify=False, allow_redirects=True)
            response.raise_for_status()
            return response, ssl_note, None
        except requests.exceptions.RequestException as e_retry:
            return None, ssl_note, str(e_retry)
    except requests.exceptions.RequestException as e_other:
        return None, None, str(e_other)

def find_words_in_response(response, words_to_find):
    """Parses a response's text to find elements containing specific words."""
    found_matches = []
    try:
        soup = BeautifulSoup(response.text, 'lxml')
    except:
        soup = BeautifulSoup(response.text, 'html.parser')

    unique_element_texts = set()
    for phrase in words_to_find:
        text_nodes = soup.find_all(string=re.compile(re.escape(phrase), re.IGNORECASE))
        for text_node in text_nodes:
            parent_element = text_node.find_parent()
            if parent_element:
                element_text = parent_element.get_text(separator=' ', strip=True)
                if element_text and element_text not in unique_element_texts:
                    found_matches.append((phrase, element_text))
                    unique_element_texts.add(element_text)
    return found_matches

def scan_domain(domain, words, total_domains, no_color):
    """Worker function to scan a single domain."""
    global scanned_count, sites_with_hits
    
    with print_lock:
        scanned_count += 1
        print(f"[{scanned_count}/{total_domains}] Scanning {domain}...")

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    response, ssl_note, err_https = get_response(f"https://{domain}")
    err_http = None

    if response is None:
        response, _, err_http = get_response(f"http://{domain}")

    with file_lock:
        if ssl_note:
            with print_lock:
                print(f"  -> [NOTE] {ssl_note}")
            with open(ERRORS_FILE, 'a', encoding='utf-8') as f:
                f.write(f"{timestamp} - {domain} - SSL NOTE: {ssl_note}\n")
        
        if response is None:
            with open(ERRORS_FILE, 'a', encoding='utf-8') as f:
                f.write(f"{timestamp} - {domain} - Connection Failure\n")
                if err_https: f.write(f"  - HTTPS Error: {err_https}\n")
                if err_http: f.write(f"  - HTTP Error: {err_http}\n")
            with print_lock:
                print(f"  -> [ERROR] Could not connect to {domain} on either protocol.")
            return

    final_url = response.url
    scan_key = get_base_domain(final_url)
    
    with file_lock:
        if not scan_key:
            with print_lock:
                print(f"  -> [ERROR] Could not parse final domain from {final_url}")
            with open(ERRORS_FILE, 'a', encoding='utf-8') as f:
                f.write(f"{timestamp} - {domain} - Could not parse final domain from {final_url}\n")
            return

        if scan_key in scanned_base_domains:
            with print_lock:
                print(f"  -> [SKIP] {domain} resolves to the already scanned base domain: {scan_key}")
            return
        
        scanned_base_domains.add(scan_key)

    matches = find_words_in_response(response, words)
    
    with file_lock:
        if matches:
            sites_with_hits += 1
            protocol = urlparse(response.url).scheme.upper()
            with print_lock:
                print(f"  -> [MATCH] Found keywords on {domain} (final: {scan_key}) via {protocol}.")
            
            with open(MATCHES_FILE, 'a', encoding='utf-8') as f:
                header = f"{timestamp} - {scan_key} ({domain}):\n"
                f.write(header)
                for phrase, element_text in matches:
                    f.write(f"  - [{phrase}]: {element_text}\n")
                    with print_lock:
                        if not no_color:
                            pattern = re.compile(re.escape(phrase), re.IGNORECASE)
                            colored_text = pattern.sub(lambda m: f"{Fore.GREEN}{m.group(0)}{Style.RESET_ALL}", element_text)
                            print(f"    - [{phrase}]: {colored_text}")
                        else:
                            print(f"    - [{phrase}]: {element_text}")
                f.write("\n")
        else:
            with open(NO_MATCHES_FILE, 'a', encoding='utf-8') as f:
                f.write(f"{timestamp} - {scan_key} ({domain})\n")
            with print_lock:
                print(f"  -> [NO MATCH] Scanned {domain}, but no keywords were found.")


def create_example_file(filename, content):
    """Creates a file with example content if it doesn't exist."""
    if not os.path.exists(filename):
        with print_lock:
            print(f"{filename} not found. Creating an example file.")
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)

def main():
    """Main function to run the website checker."""
    colorama.init(autoreset=True)
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    os.makedirs(LOGS_DIR, exist_ok=True)
    os.makedirs(LISTS_DIR, exist_ok=True)

    config = load_config(CONFIG_FILE)
    if config is None:
        print(f"{Fore.RED}Error: Configuration file '{CONFIG_FILE}' not found or is empty.")
        create_example_file(
            CONFIG_FILE,
            '# Scrape Goat Configuration\n\n'
            '[hatch-act]\n'
            'url = https://raw.githubusercontent.com/cisagov/dotgov-data/main/current-federal.csv\n'
            'default = yes\n'
            'keywords = Privacy, Security, "Terms of Service"\n\n'
            '[tech-news]\n'
            'url = https://raw.githubusercontent.com/j-c-s/tech-news-aggregator-list/main/feed_list.csv\n'
            'keywords = "vulnerability management", CVE, exploit, patch\n'
        )
        print(f"An example '{CONFIG_FILE}' has been created.")
        return

    default_list_name = get_default_list_name(config)

    parser = argparse.ArgumentParser(description="Scan websites for keywords and phrases from a file.")
    parser.add_argument('-i', '--input', type=str, help=f'Specify a custom local input file (in {LISTS_DIR}/), overriding config.')
    parser.add_argument('-l', '--list-name', type=str, default=default_list_name, help=f'Specify list from {CONFIG_FILE}. Default: "{default_list_name}".')
    parser.add_argument('-t', '--threads', type=int, default=10, help='Number of concurrent threads to use for scanning. Default: 10.')
    parser.add_argument('-o', '--in-order', action='store_true', help='Scan domains in order (disables randomization).')
    parser.add_argument('-c', '--no-color', action='store_true', help='Disable colorized output in the console.')
    parser.add_argument('-u', '--update-list', action='store_true', help='Download the latest version of the selected domain list.')
    parser.add_argument('--clobber', action='store_true', help='Overwrite (clobber) the output files instead of appending.')
    args = parser.parse_args()
    
    selected_list_name = args.list_name
    if not selected_list_name or not config.has_section(selected_list_name):
        print(f"{Fore.RED}Error: List name '{selected_list_name}' not found in {CONFIG_FILE}.")
        print(f"Available lists are: {', '.join(config.sections())}")
        return
    
    try:
        url_to_use = config.get(selected_list_name, 'url')
        keywords_str = config.get(selected_list_name, 'keywords')
        words = parse_keywords(keywords_str)
    except configparser.NoOptionError as e:
        print(f"{Fore.RED}Error in config section '[{selected_list_name}]': Missing option '{e.option}'.")
        return

    filename_base = os.path.basename(unquote(urlparse(url_to_use).path))
    local_filename = os.path.join(LISTS_DIR, filename_base)

    if args.update_list:
        update_domain_list(local_filename, url_to_use)
        return

    print("--- Scrape Goat: Website Keyword Checker ---")
    print("-> Press Ctrl+C at any time to stop the scan.")
    
    if args.input:
        input_file_to_load = os.path.join(LISTS_DIR, args.input)
        print(f"-> Using local override file: '{input_file_to_load}'")
    else:
        print(f"-> Using list '{selected_list_name}' from config.")
        input_file_to_load = local_filename
        if not os.path.exists(input_file_to_load):
            print(f"-> Local file '{input_file_to_load}' not found for list '{selected_list_name}'.")
            update_domain_list(local_filename, url_to_use)

    domains = load_domains(input_file_to_load)

    if domains is None or not words:
        print("Exiting due to missing domain file or empty keyword list in config.")
        return

    if not args.in_order:
        print("-> Randomizing the domain list (default behavior). Use --in-order to disable.")
        random.shuffle(domains)
    else:
        print("-> Scanning domains in order as requested.")

    if args.clobber:
        print("-> Clobbering (overwriting) previous output files as requested.")
        open(MATCHES_FILE, 'w').close()
        open(NO_MATCHES_FILE, 'w').close()
        open(ERRORS_FILE, 'w').close()
    else:
        print("-> Appending to existing output files (use --clobber to overwrite).")

    print(f"\nScanning {len(domains)} domains using {args.threads} threads...\n")
    
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.threads) as executor:
            # Submit all domains to the executor
            futures = [executor.submit(scan_domain, domain, words, len(domains), args.no_color) for domain in domains]
            # Wait for all futures to complete (or for KeyboardInterrupt)
            concurrent.futures.wait(futures)

    except KeyboardInterrupt:
        print("\n\n--- Scan Interrupted by User (Ctrl+C) ---")
        # The executor will be shut down automatically by the 'with' statement
    
    finally:
        print("\n--- Scan Summary ---")
        if scanned_count > 0:
            print(f"Found keywords/phrases on {sites_with_hits} out of {scanned_count} sites scanned.")
        else:
            print("No sites were scanned.")
        print(f"Results have been saved to the '{LOGS_DIR}/' directory.")

if __name__ == "__main__":
    main()


