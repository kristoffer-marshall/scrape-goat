# **Scrape Goat: Website Keyword Scanner**

Scrape Goat is a powerful and flexible Python script designed to scan a list of websites for specific keywords and phrases. It automates the process of checking web pages for content, handling common issues like redirects and SSL errors, and logging the results in a clear, organized manner.  
It's an ideal tool for researchers, compliance auditors, or anyone needing to verify the presence of specific text across a large number of domains.

## **Features**

* **Config-Driven Scans**: Manages multiple domain lists and their associated keywords in a single, easy-to-edit config.ini file.  
* **Targeted Keyword & Phrase Matching**: Searches for an unlimited number of keywords and multi-word phrases within the HTML content of websites.  
* **Contextual Extraction**: Instead of just reporting a match, it extracts the full text of the HTML element where the keyword was found, providing valuable context.  
* **Flexible Domain Input**:  
  * Supports multiple lists defined in config.ini.  
  * Allows for a local file override (.csv or .txt) for quick, one-off scans.  
* **Automated List Management**:  
  * Can download and update any domain list from its source URL using the \--update-list flag.  
  * Automatically fetches a list from its URL if it's not found locally during a normal scan.  
* **Intelligent Deduplication**: Avoids scanning the same base domain multiple times (e.g., treats www.example.gov and api.example.gov as example.gov).  
* **Robust Scanning**:  
  * Automatically follows HTTP/HTTPS redirects.  
  * Bypasses SSL/TLS verification errors to analyze content, logging the error for reference.  
  * Tries both https:// and http:// protocols for each domain.  
* **Organized, Persistent Logging**:  
  * Saves all output to a logs/ directory.  
  * Appends results to matches.log, no\_matches.log, and errors.log by default.  
  * Includes a \--clobber option to overwrite previous logs.  
  * Timestamps every entry for clear record-keeping.  
* **User-Friendly Operation**:  
  * Randomizes the scan order by default.  
  * Provides an option (--in-order) to scan sequentially.  
  * Highlights matches in the console with green text (can be disabled).  
  * Allows the user to gracefully stop the scan at any time using Ctrl+C.

## **Setup**

1. **Python**: Ensure you have Python 3.6+ installed.  
2. **Dependencies**: Install the required Python libraries using the provided file:  
   pip install \-r requirements.txt

3. **Configuration**:  
   * Edit the config.ini file to define your domain lists and the keywords you want to search for.  
   * You can add as many list sections (e.g., \[my-custom-list\]) as you need.  
   * Set default \= yes for the list you want to run when no other is specified. The script will automatically create domain-lists/ and logs/ directories on first run.

## **Usage**

Execute the script from your terminal. It will use the default list from your config.ini unless you specify another.  
\# Run a standard scan using the default list in the config  
\# If the list file isn't in 'domain-lists/', it will be downloaded automatically.  
python scrapegoat.py

\# Run a scan using a specific list from the config  
python scrapegoat.py \--list-name tech-news

\# Force an update of a specific domain list from its source URL  
\# The file will be saved in the 'domain-lists/' directory  
python scrapegoat.py \--list-name hatch-act \--update-list

\# Use a temporary local file (must be in the 'domain-lists/' directory)  
\# and overwrite old logs  
python scrapegoat.py \--input my\_temp\_domains.txt \--clobber

### **Command-Line Arguments**

| Flag | Alias | Description |
| :---- | :---- | :---- |
| \--help | \-h | Show the help message and exit. |
| \--list-name \[NAME\] | \-l | Specify the list to use from config.ini. |
| \--input \[FILE\] | \-i | **Override config:** Use a custom local input file (must be in domain-lists/) for domains. |
| \--update-list | \-u | Download/update the selected domain list from its source URL and exit. |
| \--in-order | \-o | Scan domains sequentially (disables default randomization). |
| \--no-color | \-c | Disable colorized output in the console. |
| \--clobber |  | Overwrite (clobber) the output files in the logs/ directory instead of appending to them. |

### **Output Files**

All output files are located in the logs/ directory.

* **matches.log**: A timestamped list of domains where keywords were found, including the final URL, the initial domain, and the text of the element containing each match.  
* **no\_matches.log**: A timestamped list of domains that were successfully scanned but contained none of the specified keywords.  
* **errors.log**: A timestamped log of any domains that could not be reached or resulted in an error (e.g., connection timeouts, DNS failures, SSL warnings).