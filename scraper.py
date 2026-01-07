import requests
import json
import logging
import os
import re
import argparse
from datetime import datetime
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class FlareSolverrClient:
    def __init__(self, base_url="http://localhost:8191/v1"):
        self.base_url = base_url
        self.session_id = None

    def create_session(self):
        """Creates a new browser session in FlareSolverr."""
        payload = {
            "cmd": "sessions.create"
        }
        try:
            logging.info("Creating FlareSolverr session...")
            response = requests.post(self.base_url, json=payload)
            response.raise_for_status()
            data = response.json()
            if data.get('status') == 'ok':
                self.session_id = data.get('session')
                logging.info(f"Session created: {self.session_id}")
                return self.session_id
            else:
                logging.error(f"Failed to create session: {data}")
                return None
        except requests.exceptions.RequestException as e:
            logging.error(f"Error connecting to FlareSolverr: {e}")
            return None

    def destroy_session(self):
        """Destroys the current browser session."""
        if not self.session_id:
            return

        payload = {
            "cmd": "sessions.destroy",
            "session": self.session_id
        }
        try:
            logging.info(f"Destroying session: {self.session_id}")
            requests.post(self.base_url, json=payload)
            self.session_id = None
        except requests.exceptions.RequestException as e:
            logging.error(f"Error destroying session: {e}")

    def get_content(self, url, max_timeout=60000):
        """Fetching content using the active session."""
        if not self.session_id:
            if not self.create_session():
                return None

        payload = {
            "cmd": "request.get",
            "url": url,
            "session": self.session_id,
            "maxTimeout": max_timeout
        }
        
        try:
            logging.info(f"Scraping URL: {url}")
            response = requests.post(self.base_url, json=payload)
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') == 'ok':
                return data.get('solution', {}).get('response') # Returns HTML
            else:
                logging.error(f"Error scraping page: {data}")
                return None
                
        except requests.exceptions.RequestException as e:
            logging.error(f"Request failed: {e}")
            return None

class CamelScraper:
    BASE_URL = "https://camelcamelcamel.com"

    def __init__(self):
        self.client = FlareSolverrClient()

    def _parse_search_results(self, html):
        """Parses search results HTML and extracts product data."""
        soup = BeautifulSoup(html, 'html.parser')
        products = []
        
        for result_div in soup.select('div.search-result'):
            try:
                # Get title and ASIN
                title_tag = result_div.select_one('p.product-title a')
                if not title_tag:
                    continue
                    
                title = title_tag.get_text(strip=True)
                asin = title_tag.get('x-camel-asin', 'N/A')
                product_url = title_tag.get('href', '')
                
                # Get prices (Amazon, 3rd Party New, 3rd Party Used)
                prices = {}
                price_rows = result_div.select('tr.watch_row')
                for row in price_rows:
                    price_type_tag = row.select_one('td.price-type a')
                    price_value_tag = row.select_one('span.cur-price')
                    
                    if price_type_tag and price_value_tag:
                        price_type = price_type_tag.get_text(strip=True)
                        price_value = price_value_tag.get_text(strip=True)
                        prices[price_type] = price_value
                
                products.append({
                    "asin": asin,
                    "title": title,
                    "url": product_url,
                    "prices": prices
                })
            except Exception as e:
                logging.warning(f"Error parsing product: {e}")
                continue
                
        return products

    def _get_max_page(self, html):
        """Finds the last page number from pagination links."""
        soup = BeautifulSoup(html, 'html.parser')
        # Pagination uses p= parameter (e.g., /search?sq=nike&p=2)
        page_links = soup.find_all('a', href=re.compile(r'p=\d+'))
        
        max_page = 1
        for link in page_links:
            href = link.get('href', '')
            match = re.search(r'p=(\d+)', href)
            if match:
                page_num = int(match.group(1))
                if page_num > max_page:
                    max_page = page_num
        return max_page

    def search(self, query, max_pages=None):
        """
        Searches for products on CamelCamelCamel.
        
        Args:
            query: The search query string.
            max_pages: Maximum number of pages to scrape. None for all pages.
            
        Returns:
            A list of product dictionaries.
        """
        all_products = []
        page = 1
        
        # Fetch first page to determine max pages
        first_url = f"{self.BASE_URL}/search?sq={requests.utils.quote(query)}"
        html = self.client.get_content(first_url)
        
        if not html:
            logging.error("Failed to fetch first page.")
            return all_products
            
        # Determine max pages available
        available_max_page = self._get_max_page(html)
        if max_pages is None:
            max_pages = available_max_page
        else:
            max_pages = min(max_pages, available_max_page)
            
        logging.info(f"Total pages to scrape: {max_pages}")
        
        # Parse first page
        products = self._parse_search_results(html)
        all_products.extend(products)
        logging.info(f"Page 1: Found {len(products)} products.")
        
        # Loop through remaining pages
        for page in range(2, max_pages + 1):
            url = f"{self.BASE_URL}/search?sq={requests.utils.quote(query)}&p={page}"
            html = self.client.get_content(url)
            
            if not html:
                logging.warning(f"Failed to fetch page {page}. Stopping.")
                break
                
            products = self._parse_search_results(html)
            if not products:
                logging.info(f"Page {page}: No products found. Stopping.")
                break
                
            all_products.extend(products)
            logging.info(f"Page {page}: Found {len(products)} products.")
            
        return all_products

    def _calculate_statistics(self, products):
        """Calculates statistics from scraped products."""
        stats = {
            "total_products": len(products),
            "price_analysis": {
                "Amazon": {"count": 0, "sum": 0.0, "min": float('inf'), "max": float('-inf'), "average": 0.0},
                "3rd Party New": {"count": 0, "sum": 0.0, "min": float('inf'), "max": float('-inf'), "average": 0.0},
                "3rd Party Used": {"count": 0, "sum": 0.0, "min": float('inf'), "max": float('-inf'), "average": 0.0}
            },
            "products_with_no_prices": 0
        }

        for product in products:
            prices = product.get("prices", {})
            has_price = False
            for price_type, price_str in prices.items():
                if price_type in stats["price_analysis"]:
                    # Clean price string
                    clean_price = re.sub(r'[^\d.]', '', price_str)
                    if clean_price:
                        try:
                            price = float(clean_price)
                            has_price = True
                            p_stats = stats["price_analysis"][price_type]
                            p_stats["count"] += 1
                            p_stats["sum"] += price
                            p_stats["min"] = min(p_stats["min"], price)
                            p_stats["max"] = max(p_stats["max"], price)
                        except ValueError:
                            pass
            
            if not has_price:
                stats["products_with_no_prices"] += 1

        # Finalize averages and handle infinities
        for p_type, p_data in stats["price_analysis"].items():
            if p_data["count"] > 0:
                p_data["average"] = round(p_data["sum"] / p_data["count"], 2)
            else:
                p_data["min"] = None
                p_data["max"] = None
            del p_data["sum"] # Remove sum from final output as it's not very useful

        return stats


    def save_results(self, query, products):
        """Saves the results to a JSON file in a folder named after the query."""
        # Sanitize folder name
        safe_query = re.sub(r'[^\w\s-]', '', query).strip().replace(' ', '_')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        folder_name = f"{safe_query}_{timestamp}"
        
        os.makedirs(folder_name, exist_ok=True)
        
        file_path = os.path.join(folder_name, "results.json")
        
        output = {
            "query": query,
            "timestamp": timestamp,
            "total_products": len(products),
            "products": products
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
            
        logging.info(f"Results saved to: {file_path}")

        # Calculate and save statistics
        stats = self._calculate_statistics(products)
        stats_path = os.path.join(folder_name, "stats.json")
        with open(stats_path, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
        logging.info(f"Statistics saved to: {stats_path}")

        return file_path

    def close(self):
        self.client.destroy_session()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='CamelCamelCamel Scraper')
    parser.add_argument('query', type=str, help='Search query')
    parser.add_argument('--max-pages', type=int, default=None, help='Maximum number of pages to scrape (default: all)')
    
    args = parser.parse_args()
    
    scraper = CamelScraper()
    try:
        print(f"Searching for: {args.query}")
        products = scraper.search(args.query, max_pages=args.max_pages)
        
        if products:
            print(f"\nFound {len(products)} products total.")
            file_path = scraper.save_results(args.query, products)
            print(f"Results saved to: {file_path}")
        else:
            print("No products found.")
            
    finally:
        scraper.close()
