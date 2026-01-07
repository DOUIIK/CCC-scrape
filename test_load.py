import subprocess
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# More aggressive list of keywords
keywords = [
    "macbook", "ps5", "nintendo switch", "lego", "rtx 3080", 
    "iphone 16", "samsung s24", "canadian goose", "air pods", "kindle",
    "bose", "dyson", "monitor", "mechanical keyboard", "webcam"
]

def run_scraper(query):
    logging.info(f"--- Testing: {query} ---")
    try:
        # Scrape 2 pages to test sustained session usage
        result = subprocess.run(
            ["python", "scraper.py", query, "--max-pages", "2"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if "Found" in line and "products total" in line:
                    logging.info(f"SUCCESS: {query} -> {line.strip()}")
            return True
        else:
            logging.error(f"FAILED: {query}")
            logging.error(result.stderr)
            return False
    except Exception as e:
        logging.error(f"ERROR: {query}: {e}")
        return False

if __name__ == "__main__":
    logging.info("Starting FlareSolverr TORTURE TEST (15 keywords, 2 pages each)...")
    success_count = 0
    start_time = time.time()
    
    for keyword in keywords:
        if run_scraper(keyword):
            success_count += 1
        # Very short delay to simulate fast manual or semi-automated usage
        time.sleep(1)
        
    end_time = time.time()
    logging.info(f"\n--- TORTURE TEST SUMMARY ---")
    logging.info(f"Total Keywords: {len(keywords)}")
    logging.info(f"Success Rate: {success_count}/{len(keywords)}")
    logging.info(f"Total Time: {round(end_time - start_time, 2)} seconds")
    logging.info(f"Average time per query: {round((end_time - start_time)/len(keywords), 2)} seconds")

