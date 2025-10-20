from flask import Flask, render_template, request
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import re
from datetime import datetime

app = Flask(__name__)

def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver

def scrape_mobile_de(filters):
    driver = setup_driver()
    url = f"https://www.mobile.de/?lang=de&search[makeModelVariant]={filters['make']}&search[damageUnrepaired]={filters['damage']}&search[minPrice]={filters['min_price']}&search[maxPrice]={filters['max_price']}&search[minMileage]={filters['min_mileage']}&search[maxMileage]={filters['max_mileage']}&search[minFirstRegistration]={filters['min_year']}&search[maxFirstRegistration]={filters['max_year']}&search[gearbox]={filters['gearbox']}&search[city]={filters['city']}"
    driver.get(url)
    time.sleep(5)
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    driver.quit()

    cars = []
    listings = soup.find_all('div', class_='cldt-summary-full-item')
    print(f"mobile.de: Found {len(listings)} listings")
    for listing in listings[:10]:
        try:
            title_elem = listing.find('h2', class_='cldt-summary-title')
            title = title_elem.text.strip() if title_elem else 'N/A'
            link_elem = listing.find('a', class_='cldt-summary-titles')
            url = 'https://www.mobile.de' + link_elem['href'] if link_elem and link_elem.get('href') else 'N/A'
            cars.append({
                'website': 'mobile.de',
                'title': title,
                'url': url
            })
            print(f"mobile.de: Added car - {title}, URL: {url}")
        except Exception as e:
            print(f"mobile.de: Error processing listing - {e}")
            continue
    return cars

def scrape_autoscout24(filters):
    driver = setup_driver()
    url = f"https://www.autoscout24.de/lst/{filters['make']}?sort=price&desc=0&ustate=N%2CU&size=20&cy=D&kmfrom={filters['min_mileage']}&kmto={filters['max_mileage']}&fregfrom={filters['min_year']}&fregto={filters['max_year']}&pricefrom={filters['min_price']}&priceto={filters['max_price']}&gear={filters['gearbox']}&zip={filters['city']}"
    driver.get(url)
    time.sleep(5)
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    driver.quit()

    cars = []
    listings = soup.find_all('article', class_='cldt-summary-full-item')
    print(f"autoscout24: Found {len(listings)} listings")
    for listing in listings[:10]:
        try:
            title_elem = listing.find('h2')
            title = title_elem.text.strip() if title_elem else 'N/A'
            link_elem = listing.find('a', class_='ListItem_title__ndA4s')
            url = 'https://www.autoscout24.de' + link_elem['href'] if link_elem and link_elem.get('href') else 'N/A'
            cars.append({
                'website': 'autoscout24.de',
                'title': title,
                'url': url
            })
            print(f"autoscout24: Added car - {title}, URL: {url}")
        except Exception as e:
            print(f"autoscout24: Error processing listing - {e}")
            continue
    return cars

def scrape_ebay_kleinanzeigen(filters):
    driver = setup_driver()
    url = f"https://www.ebay-kleinanzeigen.de/s-autos/{filters['make']}/preis:{filters['min_price']}:{filters['max_price']}/km:{filters['min_mileage']}:{filters['max_mileage']}/ez:{filters['min_year']}:{filters['max_year']}/{filters['city']}/k0c216"
    driver.get(url)
    time.sleep(5)
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    driver.quit()

    cars = []
    listings = soup.find_all('article', class_='aditem')
    print(f"ebay-kleinanzeigen: Found {len(listings)} listings")
    for listing in listings[:10]:
        try:
            title_elem = listing.find('h2', class_='text-module-begin')
            title = title_elem.text.strip() if title_elem else 'N/A'
            link_elem = listing.find('a', class_='ellipsis')
            url = 'https://www.ebay-kleinanzeigen.de' + link_elem['href'] if link_elem and link_elem.get('href') else 'N/A'
            cars.append({
                'website': 'ebay-kleinanzeigen.de',
                'title': title,
                'url': url
            })
            print(f"ebay-kleinanzeigen: Added car - {title}, URL: {url}")
        except Exception as e:
            print(f"ebay-kleinanzeigen: Error processing listing - {e}")
            continue
    return cars

@app.route('/', methods=['GET', 'POST'])
def index():
    cars = []
    error = None
    if request.method == 'POST':
        filters = {
            'make': request.form.get('make', '').lower(),
            'city': request.form.get('city', ''),
            'min_mileage': request.form.get('min_mileage', '0'),
            'max_mileage': request.form.get('max_mileage', '999999'),
            'min_year': request.form.get('min_year', '1900'),
            'max_year': request.form.get('max_year', str(datetime.now().year)),
            'gearbox': request.form.get('gearbox', ''),
            'min_price': request.form.get('min_price', '0'),
            'max_price': request.form.get('max_price', '999999'),
            'damage': request.form.get('damage', '')
        }
        
        try:
            filters['min_mileage'] = int(filters['min_mileage'])
            filters['max_mileage'] = int(filters['max_mileage'])
            filters['min_year'] = int(filters['min_year'])
            filters['max_year'] = int(filters['max_year'])
            filters['min_price'] = int(filters['min_price'])
            filters['max_price'] = int(filters['max_price'])
            filters['gearbox'] = 'M' if filters['gearbox'] == 'Schaltgetriebe' else 'A' if filters['gearbox'] == 'Automatik' else ''
            filters['damage'] = 'NO' if filters['damage'] == 'Neu' else 'YES' if filters['damage'] == 'Beschädigt' else ''
        except ValueError:
            error = "Bitte geben Sie gültige numerische Werte für Preis, Kilometerstand und Jahr ein."
            return render_template('index.html', error=error, cars=[])

        mobile_cars = scrape_mobile_de(filters)
        autoscout_cars = scrape_autoscout24(filters)
        ebay_cars = scrape_ebay_kleinanzeigen(filters)
        all_cars = mobile_cars + autoscout_cars + ebay_cars
        print(f"Total cars found: {len(all_cars)}")
        
        df = pd.DataFrame(all_cars)
        if not df.empty:
            cars = df.to_dict('records')
        else:
            error = "Keine Autos gefunden, die den Kriterien entsprechen."

    return render_template('index.html', cars=cars, error=error)

if __name__ == '__main__':
    app.run(debug=True)