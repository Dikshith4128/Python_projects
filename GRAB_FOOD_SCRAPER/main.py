# Import necessary libraries
from seleniumwire import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
import json
import gzip
import time
import logging

# Define the RestaurantScraper class
class RestaurantScraper:
    def __init__(self, location_to_search):
        # Initialize class attributes
        self.location_to_search = location_to_search
        self.output_file = f'{location_to_search.replace(" ", "_")}_output_latlng.ndjson'
        self.driver = None

# Section for initializing the Chrome WebDrive
    def _initialize_driver(self):
        chrome_options = Options()
        chrome_options.add_argument('--ignore-certificate-errors')
        chrome_options.add_argument('--ignore-ssl-errors')
        chrome_options.add_argument('--proxy-server="direct://"')
        chrome_options.add_argument('--proxy-bypass-list=*')
        chrome_options.add_argument('--disable-web-security')
        chrome_options.add_argument(r'--ca-certificate=C:\Users\diksh\OneDrive\Desktop\grab_foods_restuarent_data\ca.crt')
        chrome_options.add_argument(r'--user-data-dir=C:\Users\diksh\OneDrive\Desktop\grab_foods_restuarent_data\custom_chrome_profile')
        self.driver = webdriver.Chrome(seleniumwire_options={'disable_certificate_verification': True}, options=chrome_options)

# Section for searching the location using the WebDriver
    def _search_location(self):
        search_bar = self.driver.find_element(By.ID, "location-input")
        submit_button = self.driver.find_element(By.CSS_SELECTOR, '.ant-btn.submitBtn___2roqB.ant-btn-primary')
        if search_bar:
            search_bar.clear()
            search_bar.send_keys(self.location_to_search)
            time.sleep(5)
            search_bar.send_keys(Keys.ENTER)
            time.sleep(5)
            submit_button.click()
            time.sleep(5)

# Section for gradually scrolling to the bottom of the page
    def _slow_scroll_to_bottom(self):
        start_time = time.time()
        while time.time() - start_time < 30:
            self.driver.execute_script("window.scrollBy(0, 400);")
            time.sleep(0.5)

# Section for scraping restaurant data from the loaded page
    def _scrape_restaurant_data(self):
        restaurant_list = []
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(5)
        offset = 0
        while True:
            requests = [request for request in self.driver.requests if request.response and request.url.startswith('https://portal.grab.com/foodweb/v2/search')]
            if len(requests) >= 8:
                break
        for request in requests:
            res = request.response
            if res.headers.get('Content-Encoding', '') == 'gzip':
                body_json = json.loads(gzip.decompress(res.body).decode('utf-8'))
            else:
                body_json = json.loads(res.body.decode('utf-8'))

            search_merchants = body_json.get('searchResult', {}).get('searchMerchants', [])
            for restaurant in search_merchants:
                try:
                    _data = {}
                    # Extract relevant data from the restaurant object
                    _data['Restaurant ID'] = restaurant.get('id', '')
                    _data['Restaurant Name'] = restaurant.get('address', {}).get('name', '')
                    _data['Restaurant latitude '] = restaurant.get('latlng', {}).get('latitude', '')
                    _data['Restaurant longitude'] = restaurant.get('latlng', {}).get('longitude', '')
                    _data['Estimate time of Delivery'] = restaurant.get('estimatedDeliveryTime', '')
                    _data['Restaurant Cuisine'] = restaurant.get('merchantBrief', {}).get('cuisine', '')
                    _data['Restaurant Notice'] = restaurant.get('merchantBrief', {}).get('openHours', '')
                    _data['Image Link of the Restaurant'] = restaurant.get('merchantBrief', {}).get('photoHref', '')
                    _data['Restaurant Distance from Delivery Location'] = restaurant.get('merchantBrief', {}).get('distanceInKm', '')
                    _data['Restaurant Rating'] = restaurant.get('merchantBrief', {}).get('rating', '')
                    promo_info = restaurant.get('merchantBrief', {}).get('promo', {})
                    _data['Is promo available'] = promo_info.get('hasPromo', False)
                    _data['Promotional Offers Listed for the Restaurant'] = promo_info.get('description', 'None') if _data['Is promo available'] else 'None'
                    _data['estimateDeliveryFee'] = round(float(_data['Restaurant Distance from Delivery Location']) * 3, 3) if _data['Restaurant Distance from Delivery Location'] else None

                    restaurant_list.append(_data)
                except Exception as e:
                    logging.exception(f"Error processing restaurant data: {str(e)}")
        return restaurant_list

# Section for performing quality control (QC) on the extracted data
    def _perform_qc(self, restaurant_list):
        for restaurant in restaurant_list:
            if not restaurant.get('Restaurant ID'):
                logging.warning("Missing Restaurant ID in extracted data.")

# Section for saving data to a gzipped NDJSON file
    def _save_to_ndjson_gz(self, restaurant_list):
        gzipped_file = f'{self.output_file}.gz'
        with gzip.open(gzipped_file, 'wt', encoding='utf-8') as f:
            for restaurant in restaurant_list:
                json.dump(restaurant, f, ensure_ascii=False)
                f.write('\n')
        print(f'\nDone. Output saved to {gzipped_file}')

# Main function to run the scraper
    def run_scraper(self):
        try:
            # Initialize the WebDriver
            self._initialize_driver()
            # Load the Grab Food websit
            self.driver.get("https://food.grab.com/sg/en")
            # Search for the specified location
            self._search_location()
            # Gradually scroll to the bottom of the page
            self._slow_scroll_to_bottom()
            # Scrape restaurant data from the loaded pag
            restaurant_list = self._scrape_restaurant_data()
            # Perform quality control (QC) on the extracted data
            self._perform_qc(restaurant_list)
            # Save data to a gzipped NDJSON file
            self._save_to_ndjson_gz(restaurant_list)
        except Exception as e:
            logging.exception(f"An error occurred: {str(e)}")
        finally:
            # Close the WebDriver
            if self.driver:
                self.driver.quit()

# Main function to initiate the scraper for specified locations
def main():
    locations_to_search = ["Ang Mo Kio Avenue 10, #01-1574, Singapore, 560456", "Choa Chu Kang North 6, Singapore, 689577"]
    for location in locations_to_search:
        scraper_instance = RestaurantScraper(location)
        scraper_instance.run_scraper()

# Run the main function if the script is executed directl
if __name__ == "__main__":
    main()
