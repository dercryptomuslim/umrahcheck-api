#!/usr/bin/env python3
"""
🎭 Playwright Hotel Price Scraper for UmrahCheck
Real-time hotel price scraping from booking platforms
"""
import asyncio
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, date
import logging
from dataclasses import dataclass
import re
from urllib.parse import quote, urlencode
import sentry_sdk
import time

logger = logging.getLogger(__name__)

# Cache für Preise (60 Sekunden TTL)
CACHE = {}  # {(key): (value, expires_ts)}

# Rate limiting per domain
DOMAIN_SEMAPHORES = {
    "booking.com": asyncio.Semaphore(2),
    "halalbooking.com": asyncio.Semaphore(2),
    "hotels.com": asyncio.Semaphore(2)
}

# Cookie selectors für verschiedene Plattformen
COOKIE_SELECTORS = [
    'button#onetrust-accept-btn-handler',
    'button:has-text("Akzeptieren")',
    'button:has-text("Accept")',
    'button:has-text("Accept all")',
    'button[data-testid="cookie-accept"]',
    '[aria-label*="Accept"]',
    'button[class*="accept"]',
]

@dataclass
class HotelPriceResult:
    """Hotel price scraping result"""
    hotel_name: str
    platform: str
    price: float
    currency: str
    total_price: float
    nights: int
    availability: bool
    scraped_at: datetime
    url: str
    checkin: str
    checkout: str
    adults: int
    rooms: int
    error: Optional[str] = None

class HotelPriceScraper:
    """Playwright-based hotel price scraper with customer date support"""
    
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.playwright = None
        # Mapping von Hotel-Namen zu Platform-spezifischen Slugs/IDs
        self.hotel_mappings = {
            "swissôtel al maqam makkah": {
                "booking": "hotel/sa/swissotel-makkah",
                "halalbooking": "swissotel-al-maqam-makkah"
            },
            "conrad makkah": {
                "booking": "hotel/sa/conrad-makkah",
                "halalbooking": "conrad-makkah"
            },
            "hilton makkah convention hotel": {
                "booking": "hotel/sa/hilton-makkah-convention",
                "halalbooking": "hilton-makkah-convention-hotel"
            },
            # Weitere Mappings können aus Airtable geladen werden
        }
        
    async def initialize(self):
        """Initialize Playwright browser"""
        try:
            self.playwright = await async_playwright().start()
            # Use Chromium in headless mode for server deployment
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-blink-features=AutomationControlled']
            )
            logger.info("✅ Playwright browser initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Playwright: {e}")
            sentry_sdk.capture_exception(e)
            raise
    
    async def close(self):
        """Close browser and cleanup"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    def build_booking_url(self, hotel_slug: str, checkin: str, checkout: str, adults: int = 2, rooms: int = 1, children: int = 0, currency: str = "EUR") -> str:
        """Build Booking.com URL with customer-specific parameters"""
        base_url = f"https://www.booking.com/{hotel_slug}.de.html"
        params = {
            "checkin": checkin,
            "checkout": checkout,
            "group_adults": adults,
            "group_children": children,
            "no_rooms": rooms,
            "selected_currency": currency,
            "lang": "de",
            # Affiliate parameter wenn vorhanden
            # "aid": "your_affiliate_id"
        }
        return f"{base_url}?{urlencode(params)}"
    
    def build_halalbooking_url(self, hotel_slug: str, checkin: str, checkout: str, adults: int = 2, rooms: int = 1, children: int = 0, currency: str = "EUR") -> str:
        """Build HalalBooking.com URL with customer-specific parameters"""
        base_url = f"https://www.halalbooking.com/hotels/{hotel_slug}"
        params = {
            "checkin": checkin,
            "checkout": checkout,
            "adults": adults,
            "children": children,
            "rooms": rooms,
            "currency": currency,
            "lang": "de",
        }
        return f"{base_url}?{urlencode(params)}"
    
    async def click_cookies(self, page: Page):
        """Click cookie accept buttons"""
        for selector in COOKIE_SELECTORS:
            try:
                btn = page.locator(selector).first
                if await btn.is_visible(timeout=1500):
                    await btn.click(timeout=1500)
                    await page.wait_for_timeout(500)  # Wait for cookie banner to disappear
                    return
            except:
                pass
    
    def parse_price(self, text: str, currency_fallback: str = "EUR") -> Tuple[float, str]:
        """Extract price and currency from text"""
        # Remove non-breaking spaces and normalize
        text = text.replace("\u00A0", " ").strip()
        
        # Find numbers
        number_match = re.search(r"([0-9][0-9\.\s,]+)", text)
        if not number_match:
            return None, None
            
        # Clean and convert number
        raw = number_match.group(1).replace(".", "").replace(" ", "").replace(",", ".")
        try:
            amount = float(raw)
        except:
            return None, None
        
        # Detect currency
        if "€" in text or "EUR" in text:
            currency = "EUR"
        elif "SAR" in text or "ر.س" in text:
            currency = "SAR"
        elif "$" in text or "USD" in text:
            currency = "USD"
        else:
            currency = currency_fallback
            
        return amount, currency
    
    async def scrape_booking_com(
        self, 
        hotel_name: str, 
        city: str,
        checkin: str,
        checkout: str,
        adults: int = 2,
        rooms: int = 1,
        children: int = 0,
        currency: str = "EUR"
    ) -> HotelPriceResult:
        """Scrape hotel prices from Booking.com"""
        
        # Use rate limiting
        domain = "booking.com"
        semaphore = DOMAIN_SEMAPHORES.get(domain, asyncio.Semaphore(1))
        
        async with semaphore:
            # Track performance with Sentry
            with sentry_sdk.start_span(op="scrape.booking", description=f"Scrape {hotel_name}"):
                try:
                    # Get hotel slug from mapping
                    hotel_key = hotel_name.lower()
                    hotel_slug = self.hotel_mappings.get(hotel_key, {}).get("booking")
                    
                    if not hotel_slug:
                        # Fallback to search if no mapping exists
                        search_query = f"{hotel_name} {city}"
                        url = f"https://www.booking.com/search.html?ss={quote(search_query)}&checkin={checkin}&checkout={checkout}&group_adults={adults}&no_rooms={rooms}&group_children={children}&selected_currency={currency}"
                    else:
                        # Direct hotel page with customer dates
                        url = self.build_booking_url(hotel_slug, checkin, checkout, adults, rooms, children, currency)
                    
                    # Create new page with context
                    page = await self.browser.new_page()
                    
                    # Block images and fonts to speed up loading
                    await page.route("**/*", lambda route: route.abort() if route.request.resource_type in ["image", "font"] else route.continue_())
                    
                    # Set realistic headers
                    await page.set_extra_http_headers({
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                        'Accept-Language': 'de-DE,de;q=0.9,en;q=0.8'
                    })
                    
                    logger.info(f"🔍 Booking.com URL: {url}")
                    
                    # Navigate with timeout
                    await page.goto(url, wait_until='domcontentloaded', timeout=45000)
                    
                    # Handle cookies
                    await self.click_cookies(page)
                    
                    # Wait for content to load
                    try:
                        await page.wait_for_load_state("networkidle", timeout=15000)
                    except:
                        pass  # Continue even if networkidle times out
                    
                    # Calculate nights for price calculation
                    checkin_date = datetime.fromisoformat(checkin)
                    checkout_date = datetime.fromisoformat(checkout)
                    nights = (checkout_date - checkin_date).days
                    
                    # Multiple selectors for price extraction (robust fallbacks)
                    price_selectors = [
                        '[data-testid="price-and-discounted-price"]',
                        '[data-testid="price-summary"]',
                        '.bui-price-display__value',
                        '.prco-valign-middle-helper',
                        '[class*="price"]:has-text("€")',
                        '[class*="rate"]:has-text("€")',
                    ]
                    
                    price_text = None
                    for selector in price_selectors:
                        try:
                            element = page.locator(selector).first
                            if await element.is_visible(timeout=2000):
                                price_text = await element.inner_text(timeout=2000)
                                if price_text and ("€" in price_text or "EUR" in price_text or any(c.isdigit() for c in price_text)):
                                    break
                        except:
                            continue
                    
                    # Parse price if found
                    if price_text:
                        amount, currency_detected = self.parse_price(price_text, currency)
                        if amount:
                            # Check if it's per night or total
                            total_price = amount * nights if "pro Nacht" in price_text or "per night" in price_text else amount
                            per_night = amount if "pro Nacht" in price_text or "per night" in price_text else amount / nights
                            
                            result = HotelPriceResult(
                                hotel_name=hotel_name,
                                platform="Booking.com",
                                price=per_night,
                                currency=currency_detected or currency,
                                total_price=total_price,
                                nights=nights,
                                availability=True,
                                scraped_at=datetime.now(),
                                url=url,
                                checkin=checkin,
                                checkout=checkout,
                                adults=adults,
                                rooms=rooms
                            )
                        else:
                            raise Exception(f"Could not parse price from: {price_text}")
                    else:
                        raise Exception("No price found on page")
                
                    await page.close()
                    return result
                    
                except Exception as e:
                    logger.error(f"Booking.com scraping failed: {e}")
                    sentry_sdk.capture_exception(e)
                    
                    return HotelPriceResult(
                    hotel_name=hotel_name,
                    platform="Booking.com",
                    price=0,
                    currency=currency,
                    total_price=0,
                    nights=(datetime.fromisoformat(checkout) - datetime.fromisoformat(checkin)).days,
                    availability=False,
                    scraped_at=datetime.now(),
                    url="",
                    checkin=checkin,
                    checkout=checkout,
                    adults=adults,
                    rooms=rooms,
                    error=str(e)
                )
    
    async def scrape_hotels_com(
        self,
        hotel_name: str,
        city: str,
        checkin: str,
        checkout: str
    ) -> HotelPriceResult:
        """Scrape hotel prices from Hotels.com"""
        
        with sentry_sdk.start_span(op="scrape.hotels", description=f"Scrape {hotel_name}"):
            try:
                page = await self.browser.new_page()
                
                # Build search URL for Hotels.com
                search_query = f"{hotel_name} {city}"
                url = f"https://www.hotels.com/search.do?q-destination={quote(search_query)}&q-check-in={checkin}&q-check-out={checkout}"
                
                await page.goto(url, wait_until='networkidle', timeout=30000)
                
                # Wait for results
                await page.wait_for_selector('[data-testid="property-listing"]', timeout=10000)
                
                # Extract first result
                first_result = await page.query_selector('[data-testid="property-listing"]')
                
                if first_result:
                    # Extract hotel name
                    name_element = await first_result.query_selector('h3')
                    found_name = await name_element.inner_text() if name_element else ""
                    
                    # Extract price
                    price_element = await first_result.query_selector('[data-testid="price"]')
                    price_text = await price_element.inner_text() if price_element else ""
                    
                    # Parse price
                    price_match = re.search(r'[\d,]+', price_text)
                    price = float(price_match.group().replace(',', '')) if price_match else 0
                    
                    result = HotelPriceResult(
                        hotel_name=found_name or hotel_name,
                        platform="Hotels.com",
                        price=price,
                        currency="EUR",
                        total_price=price,
                        nights=1,
                        availability=price > 0,
                        scraped_at=datetime.now(),
                        url=url,
                        checkin=checkin,
                        checkout=checkout,
                        adults=2,
                        rooms=1
                    )
                else:
                    result = HotelPriceResult(
                        hotel_name=hotel_name,
                        platform="Hotels.com",
                        price=0,
                        currency="EUR",
                        total_price=0,
                        nights=1,
                        availability=False,
                        scraped_at=datetime.now(),
                        url=url,
                        checkin=checkin,
                        checkout=checkout,
                        adults=2,
                        rooms=1,
                        error="No results found"
                    )
                
                await page.close()
                return result
                
            except Exception as e:
                logger.error(f"Hotels.com scraping failed: {e}")
                sentry_sdk.capture_exception(e)
                
                return HotelPriceResult(
                    hotel_name=hotel_name,
                    platform="Hotels.com",
                    price=0,
                    currency="EUR",
                    total_price=0,
                    nights=1,
                    availability=False,
                    scraped_at=datetime.now(),
                    url="",
                    checkin=checkin,
                    checkout=checkout,
                    adults=2,
                    rooms=1,
                    error=str(e)
                )
    
    async def scrape_multiple_platforms(
        self,
        hotel_name: str,
        city: str,
        checkin: str,
        checkout: str
    ) -> List[HotelPriceResult]:
        """Scrape prices from multiple platforms concurrently"""
        
        # Run scrapers concurrently
        results = await asyncio.gather(
            self.scrape_booking_com(hotel_name, city, checkin, checkout),
            self.scrape_hotels_com(hotel_name, city, checkin, checkout),
            return_exceptions=True
        )
        
        # Filter out exceptions and return valid results
        valid_results = []
        for result in results:
            if isinstance(result, HotelPriceResult):
                valid_results.append(result)
            else:
                logger.error(f"Scraping exception: {result}")
        
        return valid_results

# Singleton instance
scraper_instance: Optional[HotelPriceScraper] = None

async def get_scraper() -> HotelPriceScraper:
    """Get or create scraper instance"""
    global scraper_instance
    if not scraper_instance:
        scraper_instance = HotelPriceScraper()
        await scraper_instance.initialize()
    return scraper_instance

async def scrape_hotel_prices_with_customer_dates(
    hotel_name: str,
    city: str,
    checkin: str,
    checkout: str,
    adults: int = 2,
    rooms: int = 1,
    children: int = 0,
    currency: str = "EUR"
) -> Dict[str, Any]:
    """Main function to scrape hotel prices with customer dates and caching"""
    
    # Create cache key
    cache_key = (hotel_name, city, checkin, checkout, adults, rooms, children, currency)
    now = time.time()
    
    # Check cache (60 seconds TTL)
    if cache_key in CACHE:
        cached_data, expires = CACHE[cache_key]
        if now < expires:
            logger.info(f"📦 Cache hit for {hotel_name}")
            return cached_data
    
    logger.info(f"🎭 Scraping fresh prices for {hotel_name} ({checkin} to {checkout}, {adults} adults, {rooms} rooms)")
    
    scraper = await get_scraper()
    
    # Run both scrapers in parallel
    try:
        booking_task = scraper.scrape_booking_com(hotel_name, city, checkin, checkout, adults, rooms, children, currency)
        # Add more platforms here later
        
        results = await asyncio.gather(booking_task, return_exceptions=True)
        
        # Filter valid results
        valid_results = []
        for result in results:
            if isinstance(result, HotelPriceResult):
                valid_results.append(result)
            else:
                logger.error(f"Scraping exception: {result}")
        
        # Find best price
        best_price = None
        if valid_results:
            available_results = [r for r in valid_results if r.availability and r.price > 0]
            if available_results:
                best_price = min(available_results, key=lambda r: r.price)
        
        # Calculate stay duration
        checkin_date = datetime.fromisoformat(checkin)
        checkout_date = datetime.fromisoformat(checkout)
        nights = (checkout_date - checkin_date).days
        
        response_data = {
            "hotel_name": hotel_name,
            "city": city,
            "checkin": checkin,
            "checkout": checkout,
            "nights": nights,
            "adults": adults,
            "rooms": rooms,
            "children": children,
            "currency": currency,
            "results": [
                {
                    "platform": r.platform,
                    "price_per_night": r.price,
                    "total_price": r.total_price,
                    "currency": r.currency,
                    "availability": r.availability,
                    "url": r.url,
                    "error": r.error,
                    "scraped_at": r.scraped_at.isoformat()
                }
                for r in valid_results
            ],
            "best_price": {
                "platform": best_price.platform,
                "price_per_night": best_price.price,
                "total_price": best_price.total_price,
                "currency": best_price.currency,
                "url": best_price.url,
                "nights": nights
            } if best_price else None,
            "scraped_at": datetime.now().isoformat(),
            "cache_expires": int(now + 60)
        }
        
        # Cache the result for 60 seconds
        CACHE[cache_key] = (response_data, now + 60)
        
        return response_data
        
    except Exception as e:
        logger.error(f"Scraping failed: {e}")
        sentry_sdk.capture_exception(e)
        raise

# Backward compatibility function
async def scrape_hotel_prices(hotel_name: str, city: str, checkin: str, checkout: str) -> Dict[str, Any]:
    """Backward compatibility wrapper"""
    return await scrape_hotel_prices_with_customer_dates(hotel_name, city, checkin, checkout)