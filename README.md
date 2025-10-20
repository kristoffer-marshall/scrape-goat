# **Scrape Goat: Website Keyword Scanner**

Scrape Goat is a powerful and flexible Python script designed to scan a list of websites for specific keywords and phrases. It automates the process of checking web pages for content, handling common issues like redirects and SSL errors, and logging the results in a clear, organized manner.  
It's an ideal tool for researchers, compliance auditors, or anyone needing to verify the presence of specific text across a large number of domains.

## **Features**

* **Keyword & Phrase Matching**: Searches for an unlimited number of keywords and multi-word phrases within the HTML content of websites.  
* **Contextual Extraction**: Instead of just reporting a match, it extracts the full text of the HTML element where the keyword was found, providing valuable context.  
* **Flexible Domain Input**: Accepts a list of domains from either a .csv (parsing the first column) or a simple .txt file.  
* **Automated List Updates**: Can download and update its default domain list (current-federal.csv) directly from the CISA .gov domain repository on GitHub.  
* **Intelligent Deduplication**: Avoids scanning the same base domain multiple times (e.g., www.example.gov and api.example.gov are both treated as example.gov).  
* **Robust Scanning**:  
  * Automatically follows HTTP/HTTPS redirects.  
  * Bypasses SSL/TLS verification errors to analyze content, logging the error for reference.  
  * Tries both https:// and http:// protocols for each domain.  
* **Organized, Real-Time Logging**:  
  * Appends results to matches.txt, no\_matches.txt, and errors.txt in real-time by default.  
  * Includes a \--clobber option to overwrite previous logs.  
  * Timestamps every entry for clear record-keeping.  
* **User-Friendly Operation**:  
  * Randomizes the scan order by default to avoid hitting servers in a predictable pattern.  
  * Provides an option (--in-order) to scan sequentially.  
  * Highlights matches in the console with green text, which can be disabled.  
  * Allows the user to gracefully stop the scan at any time by pressing the Esc key.

## **Installation**

1. **Python**: Ensure you have Python 3.6+ installed.  
2. **Dependencies**: Install the required Python libraries using the requirements.txt file.  
   pip install \-r requirements.txt

## **Usage**

1. **Configure Keywords**: Edit the words.txt file and add the keywords or phrases you want to search for, with one entry per line. If the file doesn't exist, the script will create an example for you.  
2. **Prepare Domain List**:  
   * By default, the script looks for current-federal.csv. You can download this by running the script with the \-u flag.  
   * Alternatively, you can specify your own list with the \-i flag.  
3. **Run the Script**: Execute the script from your terminal.  
   \# Run a standard scan using the default domain list  
   python site\_checker.py

   \# Update the default domain list  
   python site\_checker.py \--update-list

   \# Use a custom domain list and scan in order  
   python site\_checker.py \--input my\_domains.txt \--in-order

   \# Overwrite previous logs instead of appending  
   python site\_checker.py \--clobber

### **Command-Line Arguments**

| Flag | Alias | Description |
| :---- | :---- | :---- |
| \--help | \-h | Show the help message and exit. |
| \--input \[FILENAME\] | \-i | Specify a custom input file for domains (.csv or .txt). |
| \--update-list | \-u | Download/update current-federal.csv from the official CISA repository and exit. |
| \--in-order | \-o | Scan domains sequentially as they appear in the file (disables default randomization). |
| \--no-color | \-c | Disable colorized output in the console. |
| \--clobber |  | Overwrite (clobber) the output files instead of appending to them. |

### **Output Files**

* **matches.txt**: Contains a timestamped list of domains where keywords were found, the final URL, the initial domain searched, and the full text of the element containing each match.  
* **no\_matches.txt**: A timestamped list of domains that were successfully scanned but contained none of the specified keywords.  
* **errors.txt**: A timestamped log of any domains that could not be reached or resulted in an error (e.g., connection timeouts, DNS failures, SSL warnings).