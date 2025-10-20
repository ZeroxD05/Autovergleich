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
import os

app = Flask(__name__)

# === WebDriver Setup ===
def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver

# === Scraping mobile.de ===
def scrape_mobile_de(filters):
    driver = setup_driver()
    url = (
        f"https://www.mobile.de/?lang=de"
        f"&search[makeModelVariant]={filters['make']}"
        f"&search[damageUnrepaired]={filters['damage']}"
        f"&search[minPrice]={filters['min_price']}"
        f"&search[maxPrice]={filters['max_price']}"
        f"&search[minMileage]={filters['min_mileage']}"
        f"&search[maxMileage]={filters['max_mileage']}"
        f"&search[minFirstRegistration]={filters['min_year']}"
        f"&search[maxFirstRegistration]={filters['max_year']}"
        f"&search[gearbox]={filters['gearbox']}"
        f"&search[city]={filters['city']}"
    )
    driver.get(url)
    time.sleep(5)
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    driver.quit()

    cars = []
    listings = soup.find_all('div', class_='cldt-summary-full-item')
    for listing in listings[:10]:
        try:
            title_elem = listing.find('h2', class_='cldt-summary-title')
            title = title_elem.text.strip() if title_elem else 'N/A'
            link_elem = listing.find('a', class_='cldt-summary-titles')
            car_url = 'https://www.mobile.de' + link_elem['href'] if link_elem and link_elem.get('href') else 'N/A'
            cars.append({'website': 'mobile.de', 'title': title, 'url': car_url})
        except Exception:
            continue
    return cars

# === Scraping autoscout24.de ===
def scrape_autoscout24(filters):
    driver = setup_driver()
    url = (
        f"https://www.autoscout24.de/lst/{filters['make']}?sort=price&desc=0&ustate=N%2CU"
        f"&size=20&cy=D&kmfrom={filters['min_mileage']}&kmto={filters['max_mileage']}"
        f"&fregfrom={filters['min_year']}&fregto={filters['max_year']}"
        f"&pricefrom={filters['min_price']}&priceto={filters['max_price']}"
        f"&gear={filters['gearbox']}&zip={filters['city']}"
    )
    driver.get(url)
    time.sleep(5)
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    driver.quit()

    cars = []
    listings = soup.find_all('article')
    for listing in listings[:10]:
        try:
            title_elem = listing.find('h2')
            title = title_elem.text.strip() if title_elem else 'N/A'
            link_elem = listing.find('a', href=True)
            car_url = 'https://www.autoscout24.de' + link_elem['href'] if link_elem else 'N/A'
            cars.append({'website': 'autoscout24.de', 'title': title, 'url': car_url})
        except Exception:
            continue
    return cars

# === Scraping eBay Kleinanzeigen ===
def scrape_ebay_kleinanzeigen(filters):
    driver = setup_driver()
    url = (
        f"https://www.ebay-kleinanzeigen.de/s-autos/{filters['make']}/"
        f"preis:{filters['min_price']}:{filters['max_price']}/"
        f"km:{filters['min_mileage']}:{filters['max_mileage']}/"
        f"ez:{filters['min_year']}:{filters['max_year']}/{filters['city']}/k0c216"
    )
    driver.get(url)
    time.sleep(5)
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    driver.quit()

    cars = []
    listings = soup.find_all('article', class_='aditem')
    for listing in listings[:10]:
        try:
            title_elem = listing.find('h2', class_='text-module-begin')
            title = title_elem.text.strip() if title_elem else 'N/A'
            link_elem = listing.find('a', class_='ellipsis')
            car_url = 'https://www.ebay-kleinanzeigen.de' + link_elem['href'] if link_elem else 'N/A'
            cars.append({'website': 'ebay-kleinanzeigen.de', 'title': title, 'url': car_url})
        except Exception:
            continue
    return cars

# === Flask Routes ===
@app.route('/', methods=['GET', 'POST'])
def index():
    cars, error = [], None

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
            for key in ['min_mileage', 'max_mileage', 'min_year', 'max_year', 'min_price', 'max_price']:
                filters[key] = int(filters[key])
            filters['gearbox'] = 'M' if filters['gearbox'] == 'Schaltgetriebe' else 'A' if filters['gearbox'] == 'Automatik' else ''
            filters['damage'] = 'NO' if filters['damage'] == 'Neu' else 'YES' if filters['damage'] == 'Beschädigt' else ''
        except ValueError:
            error = "Bitte geben Sie gültige numerische Werte für Preis, Kilometerstand und Jahr ein."
            return render_template('index.html', error=error, cars=[])

        # Scraping parallel oder nacheinander
        try:
            mobile_cars = scrape_mobile_de(filters)
            autoscout_cars = scrape_autoscout24(filters)
            ebay_cars = scrape_ebay_kleinanzeigen(filters)
            all_cars = mobile_cars + autoscout_cars + ebay_cars

            df = pd.DataFrame(all_cars)
            cars = df.to_dict('records') if not df.empty else []
            if not cars:
                error = "Keine Autos gefunden, die den Kriterien entsprechen."
        except Exception as e:
            error = f"Fehler beim Abrufen der Daten: {str(e)}"

    return render_template('index.html', cars=cars, error=error)


# === Production-ready run (Render etc.) ===
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
