import os
import shutil
import re
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')

def organize_results():
    base_dir = os.getcwd()
    results_dir = os.path.join(base_dir, "results")
    
    # Create results directory if it doesn't exist
    if not os.path.exists(results_dir):
        os.makedirs(results_dir)
        logging.info(f"Created directory: {results_dir}")

    # Regex for finding result folders (e.g., query_YYYYMMDD_HHMMSS)
    # Matches any string ending with _8digits_6digits
    pattern = re.compile(r'.*_\d{8}_\d{6}$')

    moved_count = 0

    for item in os.listdir(base_dir):
        item_path = os.path.join(base_dir, item)
        
        # Skip if it's the results dir itself or not a directory
        if item == "results" or not os.path.isdir(item_path):
            continue

        if pattern.match(item):
            destination = os.path.join(results_dir, item)
            try:
                shutil.move(item_path, destination)
                logging.info(f"Moved: {item} -> results/{item}")
                moved_count += 1
            except Exception as e:
                logging.error(f"Failed to move {item}: {e}")

    if moved_count == 0:
        logging.info("No folders needed moving.")
    else:
        logging.info(f"Successfully moved {moved_count} folders.")

if __name__ == "__main__":
    organize_results()
