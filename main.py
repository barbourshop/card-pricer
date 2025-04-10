from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import requests
import os
from datetime import datetime, timedelta
import numpy as np
from dotenv import load_dotenv
import csv
import asyncio
import time
from asyncio import Semaphore
import aiohttp
import base64

# Load environment variables
load_dotenv()

app = FastAPI(title="eBay Card Pricer API")

# eBay API credentials
EBAY_APP_ID = os.getenv("EBAY_APP_ID")
EBAY_CERT_ID = os.getenv("EBAY_CERT_ID")
EBAY_DEV_ID = os.getenv("EBAY_DEV_ID")

# Keywords to exclude from listings
EXCLUDED_KEYWORDS = [
    "lot",
    "complete your set",
    "you pick",
    "u pick",
    "pick your",
    "complete set",
    "bulk",
    "pick a card",
    "pick your card"
]

class Sale(BaseModel):
    sale_date: str
    price: float
    condition: str

class ActiveListing(BaseModel):
    price: float
    condition: str
    listing_type: str  # "auction" or "buy_it_now"

class CardPriceResponse(BaseModel):
    predicted_price: float
    confidence_score: float
    recent_sales: List[Sale]
    active_listings: List[ActiveListing]
    market_analysis: dict

class GoogleSheetsResponse(BaseModel):
    success: bool
    message: str
    row_number: Optional[int] = None

class CSVResponse(BaseModel):
    success: bool
    message: str
    file_path: str

# Add token caching
_oauth_token = None
_token_expiry = None
_token_lock = asyncio.Lock()

async def get_ebay_oauth_token():
    """Get eBay OAuth token with caching"""
    global _oauth_token, _token_expiry
    
    async with _token_lock:
        # Check if we have a valid cached token
        if _oauth_token and _token_expiry and datetime.now() < _token_expiry:
            return _oauth_token
            
        # Get new token
        auth_string = f"{EBAY_APP_ID}:{EBAY_CERT_ID}"
        auth_bytes = auth_string.encode('ascii')
        base64_auth = base64.b64encode(auth_bytes).decode('ascii')
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.ebay.com/identity/v1/oauth2/token",
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Authorization": f"Basic {base64_auth}"
                },
                data={
                    "grant_type": "client_credentials",
                    "scope": "https://api.ebay.com/oauth/api_scope"
                }
            ) as response:
                if response.status != 200:
                    raise HTTPException(status_code=500, detail="Failed to get eBay OAuth token")
                
                response_data = await response.json()
                _oauth_token = response_data["access_token"]
                # Set token expiry to 1 hour before actual expiry to be safe
                _token_expiry = datetime.now() + timedelta(seconds=response_data["expires_in"] - 3600)
                return _oauth_token

# Add rate limiter class
class RateLimiter:
    def __init__(self, calls_per_second):
        self.calls_per_second = calls_per_second
        self.last_call = 0
        self.lock = asyncio.Lock()
    
    async def acquire(self):
        async with self.lock:
            now = time.time()
            time_since_last_call = now - self.last_call
            if time_since_last_call < 1.0 / self.calls_per_second:
                await asyncio.sleep(1.0 / self.calls_per_second - time_since_last_call)
            self.last_call = time.time()

# Create global rate limiter
rate_limiter = RateLimiter(calls_per_second=2)

def build_search_query(brand: str, set_name: str, year: str, 
                      player_name: Optional[str] = None,
                      card_number: Optional[str] = None,
                      card_variation: Optional[str] = None,
                      condition: str = None) -> str:
    """Build eBay search query from card details"""
    query_parts = [f"{brand} {set_name} {year}"]
    
    if player_name:
        query_parts.append(player_name)
    if card_number:
        query_parts.append(f"#{card_number}")
    if card_variation:
        query_parts.append(card_variation)
    
    return " ".join(query_parts)

def analyze_market(sales_data: List[dict], active_listings: List[dict]) -> dict:
    """Analyze market conditions based on sales and active listings"""
    if not sales_data and not active_listings:
        return {
            "market_trend": "unknown",
            "supply_level": "unknown",
            "price_trend": "unknown"
        }
    
    # Calculate average sale price
    sale_prices = [sale["price"] for sale in sales_data]
    avg_sale_price = np.mean(sale_prices) if sale_prices else 0
    
    # Calculate average active listing price
    active_prices = [listing["price"] for listing in active_listings]
    avg_active_price = np.mean(active_prices) if active_prices else 0
    
    # Determine market trend
    if avg_active_price > avg_sale_price * 1.1:
        price_trend = "increasing"
    elif avg_active_price < avg_sale_price * 0.9:
        price_trend = "decreasing"
    else:
        price_trend = "stable"
    
    # Determine supply level
    if len(active_listings) > len(sales_data) * 2:
        supply_level = "high"
    elif len(active_listings) < len(sales_data) * 0.5:
        supply_level = "low"
    else:
        supply_level = "moderate"
    
    # Determine market trend based on price and supply
    if price_trend == "increasing" and supply_level == "low":
        market_trend = "bullish"
    elif price_trend == "decreasing" and supply_level == "high":
        market_trend = "bearish"
    else:
        market_trend = "neutral"
    
    return {
        "market_trend": market_trend,
        "supply_level": supply_level,
        "price_trend": price_trend,
        "avg_sale_price": round(avg_sale_price, 2),
        "avg_active_price": round(avg_active_price, 2),
        "active_listings_count": len(active_listings),
        "recent_sales_count": len(sales_data)
    }

def predict_price(sales_data: List[dict], active_listings: List[dict]) -> tuple[float, float]:
    """Predict price based on recent sales data and active listings"""
    if not sales_data and not active_listings:
        return 0.0, 0.0
    
    # Get market analysis
    market_analysis = analyze_market(sales_data, active_listings)
    
    # Extract prices
    sale_prices = [sale["price"] for sale in sales_data]
    active_prices = [listing["price"] for listing in active_listings]
    
    # Calculate weighted average of sale prices (more recent = higher weight)
    sale_weights = np.linspace(1, 0.5, len(sale_prices)) if sale_prices else np.array([])
    weighted_sale_price = np.average(sale_prices, weights=sale_weights) if sale_prices else 0
    
    # Calculate weighted average of active listings (lower prices = higher weight)
    # This assumes buyers are more likely to purchase lower-priced listings
    active_weights = np.linspace(1, 0.7, len(active_prices)) if active_prices else np.array([])
    weighted_active_price = np.average(active_prices, weights=active_weights) if active_prices else 0
    
    # Adjust prediction based on market conditions
    if market_analysis["market_trend"] == "bullish":
        # Increase prediction if market is bullish
        predicted_price = max(weighted_sale_price, weighted_active_price) * 1.05
    elif market_analysis["market_trend"] == "bearish":
        # Decrease prediction if market is bearish
        predicted_price = min(weighted_sale_price, weighted_active_price) * 0.95
    else:
        # Neutral market - use average of both
        predicted_price = (weighted_sale_price + weighted_active_price) / 2 if weighted_active_price > 0 else weighted_sale_price
    
    # Calculate confidence score
    # Base confidence on number of data points and price consistency
    sale_confidence = min(1.0, len(sale_prices) / 10) if sale_prices else 0
    active_confidence = min(1.0, len(active_prices) / 15) if active_prices else 0
    
    # Adjust confidence based on price variance
    if len(sale_prices) > 1:
        sale_std = np.std(sale_prices)
        sale_mean = np.mean(sale_prices)
        sale_confidence *= (1 - min(1, sale_std / sale_mean))
    
    if len(active_prices) > 1:
        active_std = np.std(active_prices)
        active_mean = np.mean(active_prices)
        active_confidence *= (1 - min(1, active_std / active_mean))
    
    # Combine confidences with more weight on sales data
    confidence = (sale_confidence * 0.7) + (active_confidence * 0.3)
    
    return round(predicted_price, 2), round(confidence, 2)

def filter_price_outliers(items: List[dict], price_key: str = "price") -> List[dict]:
    """Filter out extreme price outliers using the IQR method"""
    if not items or len(items) < 4:  # Need at least 4 items for meaningful outlier detection
        return items
    
    # Extract prices
    prices = [item[price_key] for item in items]
    
    # Calculate Q1, Q3 and IQR
    q1 = np.percentile(prices, 25)
    q3 = np.percentile(prices, 75)
    iqr = q3 - q1
    
    # Define bounds for outliers (1.5 is a common multiplier for IQR method)
    lower_bound = q1 - (1.5 * iqr)
    upper_bound = q3 + (1.5 * iqr)
    
    # Filter out outliers
    filtered_items = [item for item in items if lower_bound <= item[price_key] <= upper_bound]
    
    # If we filtered out more than 50% of items, the bounds might be too tight
    # In this case, use a more lenient multiplier (2.5)
    if len(filtered_items) < len(items) * 0.5:
        lower_bound = q1 - (2.5 * iqr)
        upper_bound = q3 + (2.5 * iqr)
        filtered_items = [item for item in items if lower_bound <= item[price_key] <= upper_bound]
    
    # Print debug information about filtered items
    print(f"\nFiltered out {len(items) - len(filtered_items)} price outliers")
    print(f"Price bounds: ${lower_bound:.2f} - ${upper_bound:.2f}")
    for item in items:
        if item[price_key] < lower_bound or item[price_key] > upper_bound:
            print(f"  EXCLUDED: {item.get('title', '')} - ${item[price_key]}")
    
    return filtered_items

def filter_by_title_keywords(items: List[dict], title_key: str = "title", exclude_keywords: List[str] = None) -> List[dict]:
    """Filter out items whose titles contain any of the specified keywords"""
    if not items or not exclude_keywords:
        return items
    
    # Convert keywords to lowercase for case-insensitive matching
    exclude_keywords = [kw.lower() for kw in exclude_keywords]
    
    # Filter out items with matching keywords
    filtered_items = [
        item for item in items 
        if not any(kw in item.get(title_key, "").lower() for kw in exclude_keywords)
    ]
    
    # Print debug information about filtered items
    print(f"\nFiltered out {len(items) - len(filtered_items)} items with keywords: {exclude_keywords}")
    for item in items:
        if any(kw in item.get(title_key, "").lower() for kw in exclude_keywords):
            print(f"  EXCLUDED: {item.get(title_key, '')} - ${item.get('price', 0)}")
    
    return filtered_items

@app.get("/card-price", response_model=CardPriceResponse)
async def get_card_price(
    brand: str,
    set_name: str,
    year: str,
    condition: Optional[str] = None,
    player_name: Optional[str] = None,
    card_number: Optional[str] = None,
    card_variation: Optional[str] = None
):
    """Get predicted price for a sports card based on recent eBay sales and active listings"""
    
    # Get OAuth token (now cached)
    oauth_token = await get_ebay_oauth_token()
    
    # Build search query
    query = build_search_query(brand, set_name, year, player_name, card_number, card_variation)
    print(f"Search query: {query}")  # Debug log
    
    # Calculate date range (last 90 days, which is the maximum allowed by eBay)
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=90)
    
    # Format dates in ISO 8601 UTC format
    start_date_str = start_date.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    end_date_str = end_date.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    
    # Prepare eBay API request for sold items
    sold_url = "https://api.ebay.com/buy/browse/v1/item_summary/search"
    headers = {
        "Authorization": f"Bearer {oauth_token}",
        "Content-Type": "application/json",
        "X-EBAY-C-MARKETPLACE-ID": "EBAY-US"
    }
    
    # Build the filter for completed/sold items with date range
    sold_filter = f"itemEndDate:[{start_date_str}..{end_date_str}]"
    if condition:
        # Map condition names to eBay condition values
        condition_map = {
            "New": "NEW",
            "Like New": "NEW_OTHER",
            "Excellent": "USED_EXCELLENT",
            "Very Good": "USED_VERY_GOOD",
            "Good": "USED_GOOD",
            "Acceptable": "USED_ACCEPTABLE",
            "For Parts": "FOR_PARTS",
            "Ungraded": "UNGRADED",
            "Graded": "GRADED"
        }
        condition_value = condition_map.get(condition)
        if condition_value:
            sold_filter += f",itemCondition:{{{condition_value}}}"
    
    sold_params = {
        "q": query,
        "filter": sold_filter,
        "sort": "-endDate",  # Most recent first
        "limit": 100
    }
    
    print(f"Using sold items filter: {sold_params['filter']}")  # Debug log
    
    # Apply rate limiting before making the API call
    await rate_limiter.acquire()
    
    # Make requests to eBay API using aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.get(sold_url, headers=headers, params=sold_params) as response:
            if response.status != 200:
                response_text = await response.text()
                raise HTTPException(status_code=500, detail=f"Failed to fetch sold items from eBay: {response_text}")
            
            sold_data = await response.json()
            print(f"Number of sold items found: {len(sold_data.get('itemSummaries', []))}")  # Debug log
            
            # Process sales data
            sales_data = []
            for item in sold_data.get("itemSummaries", []):
                if "price" in item:
                    print(f"Found sold item: {item.get('title')} - ${item['price']['value']} - Condition: {item.get('condition', 'Unknown')}")  # Debug log
                    # Get the sale date from itemEndDate, which is when the auction/sale ended
                    sale_date = item.get("itemEndDate")
                    if not sale_date:
                        # Fallback to soldDate if itemEndDate is not available
                        sale_date = item.get("soldDate")
                    
                    # If both dates are None, use current date as fallback
                    if not sale_date:
                        sale_date = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
                    
                    # Only include items with the specified condition
                    item_condition = item.get("condition", "Unknown")
                    if condition is None or item_condition == condition:
                        sales_data.append({
                            "sale_date": sale_date,
                            "price": float(item["price"]["value"]),
                            "condition": item_condition,
                            "title": item.get("title", "")  # Add title to the sales data
                        })
    
    # Filter out listings with specific keywords
    sales_data = filter_by_title_keywords(sales_data, exclude_keywords=EXCLUDED_KEYWORDS)
    print(f"Number of sales after keyword filtering: {len(sales_data)}")  # Debug log
    
    # Filter out price outliers from sales data
    sales_data = filter_price_outliers(sales_data)
    print(f"Number of sales after outlier filtering: {len(sales_data)}")  # Debug log
    
    # Print remaining sales data
    print("\nRemaining sales data:")
    for sale in sales_data:
        print(f"  {sale.get('title', '')} - ${sale['price']} - {sale['condition']}")
    
    # Now get active listings
    active_filter = "buyingOptions:{FIXED_PRICE|AUCTION}"  # Include both Buy It Now and Auction listings
    
    active_params = {
        "q": query,
        "filter": active_filter,
        "sort": "price",
        "limit": 100
    }
    
    print(f"Using active listings filter: {active_params['filter']}")  # Debug log
    
    # Apply rate limiting before making the API call
    await rate_limiter.acquire()
    
    # Make requests to eBay API using aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.get(sold_url, headers=headers, params=active_params) as response:
            if response.status != 200:
                response_text = await response.text()
                raise HTTPException(status_code=500, detail=f"Failed to fetch active listings from eBay: {response_text}")
            
            active_data = await response.json()
            print(f"Number of active listings found: {len(active_data.get('itemSummaries', []))}")  # Debug log
            
            # Process active listings data
            active_listings = []
            for item in active_data.get("itemSummaries", []):
                if "price" in item:
                    print(f"Found active listing: {item.get('title')} - ${item['price']['value']} - Condition: {item.get('condition', 'Unknown')}")  # Debug log
                    listing_type = "buy_it_now" if "FIXED_PRICE" in item.get("buyingOptions", []) else "auction"
                    
                    # Only include items with the specified condition
                    item_condition = item.get("condition", "Unknown")
                    if condition is None or item_condition == condition:
                        active_listings.append({
                            "price": float(item["price"]["value"]),
                            "condition": item_condition,
                            "listing_type": listing_type,
                            "title": item.get("title", "")  # Add title to the active listings
                        })
    
    # Filter out listings with specific keywords
    active_listings = filter_by_title_keywords(active_listings, exclude_keywords=EXCLUDED_KEYWORDS)
    print(f"Number of active listings after keyword filtering: {len(active_listings)}")  # Debug log
    
    # Filter out price outliers from active listings
    active_listings = filter_price_outliers(active_listings)
    print(f"Number of active listings after outlier filtering: {len(active_listings)}")  # Debug log
    
    # Print remaining active listings
    print("\nRemaining active listings:")
    for listing in active_listings:
        print(f"  {listing.get('title', '')} - ${listing['price']} - {listing['condition']} - {listing['listing_type']}")
    
    # Get market analysis
    market_analysis = analyze_market(sales_data, active_listings)
    
    # Predict price
    predicted_price, confidence = predict_price(sales_data, active_listings)
    
    return CardPriceResponse(
        predicted_price=predicted_price,
        confidence_score=confidence,
        recent_sales=[Sale(**sale) for sale in sales_data],
        active_listings=[ActiveListing(**listing) for listing in active_listings],
        market_analysis=market_analysis
    )

@app.post("/write-to-sheets", response_model=GoogleSheetsResponse)
async def write_to_sheets(
    brand: str,
    set_name: str,
    year: str,
    condition: Optional[str] = None,
    player_name: Optional[str] = None,
    card_number: Optional[str] = None,
    card_variation: Optional[str] = None
):
    try:
        # Get card price data
        price_data = await get_card_price(
            brand=brand,
            set_name=set_name,
            year=year,
            condition=condition,
            player_name=player_name,
            card_number=card_number,
            card_variation=card_variation
        )
        
        # Prepare data for Google Sheets
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row_data = [
            current_time,
            brand,
            set_name,
            year,
            condition or "N/A",
            player_name or "N/A",
            card_number or "N/A",
            card_variation or "N/A",
            str(price_data.predicted_price),
            str(price_data.confidence_score),
            str(len(price_data.recent_sales)),
            str(len(price_data.active_listings))
        ]
        
        # Get Google Sheets service
        service = get_google_sheets_service()
        
        # Append data to the spreadsheet
        result = service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range='Sheet1!A:L',  # Adjust range based on your columns
            valueInputOption='RAW',
            insertDataOption='INSERT_ROWS',
            body={'values': [row_data]}
        ).execute()
        
        return GoogleSheetsResponse(
            success=True,
            message="Successfully wrote to Google Sheets",
            row_number=result.get('updates', {}).get('updatedRange', '').split('!')[1]
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to write to Google Sheets: {str(e)}"
        )

@app.get("/write-to-csv", response_model=CSVResponse)
async def write_to_csv(
    brand: str,
    set_name: str,
    year: str,
    condition: Optional[str] = None,
    player_name: Optional[str] = None,
    card_number: Optional[str] = None,
    card_variation: Optional[str] = None
):
    try:
        # Get card price data
        price_data = await get_card_price(
            brand=brand,
            set_name=set_name,
            year=year,
            condition=condition,
            player_name=player_name,
            card_number=card_number,
            card_variation=card_variation
        )
        
        # Prepare data for CSV
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row_data = {
            'timestamp': current_time,
            'brand': brand,
            'set_name': set_name,
            'year': year,
            'condition': condition or "N/A",
            'player_name': player_name or "N/A",
            'card_number': card_number or "N/A",
            'card_variation': card_variation or "N/A",
            'predicted_price': str(price_data.predicted_price),
            'confidence_score': str(price_data.confidence_score),
            'recent_sales_count': str(len(price_data.recent_sales)),
            'active_listings_count': str(len(price_data.active_listings)),
            'market_trend': price_data.market_analysis['market_trend'],
            'supply_level': price_data.market_analysis['supply_level'],
            'price_trend': price_data.market_analysis['price_trend']
        }
        
        # Define CSV file path
        csv_file = 'card_prices.csv'
        file_exists = os.path.exists(csv_file) and os.path.getsize(csv_file) > 0
        
        # Write to CSV
        with open(csv_file, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=row_data.keys())
            if not file_exists:
                writer.writeheader()
            writer.writerow(row_data)
        
        return CSVResponse(
            success=True,
            message="Successfully wrote to CSV file",
            file_path=csv_file
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to write to CSV: {str(e)}"
        )

# Modify process_cards_from_csv to use parallel processing
async def process_cards_from_csv(
    input_csv_path: str,
    output_csv_path: str = "card_prices.csv",
    max_concurrent: int = 5
):
    """
    Process multiple cards from an input CSV file and write results to an output CSV file.
    Uses parallel processing with asyncio to speed up processing.
    
    Args:
        input_csv_path (str): Path to the input CSV file containing card details
        output_csv_path (str): Path to write the results (default: 'card_prices.csv')
        max_concurrent (int): Maximum number of cards to process concurrently (default: 5)
    
    Returns:
        dict: Summary of processing results including success count and any errors
    """
    results = {
        'total_cards': 0,
        'successful': 0,
        'failed': 0,
        'errors': []
    }
    
    try:
        # Read input CSV
        with open(input_csv_path, 'r', newline='') as f:
            reader = csv.DictReader(f)
            cards = list(reader)
        
        results['total_cards'] = len(cards)
        
        # Process cards in batches
        batch_size = max_concurrent
        for i in range(0, len(cards), batch_size):
            batch = cards[i:i+batch_size]
            
            # Create a new event loop for this batch
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # Create a semaphore to limit concurrent processing
                semaphore = asyncio.Semaphore(max_concurrent)
                
                # Create a lock for writing to the CSV file
                csv_lock = asyncio.Lock()
                
                # Define a function to process a single card
                async def process_card(card):
                    async with semaphore:
                        try:
                            # Get card price data
                            price_data = await get_card_price(
                                brand=card['brand'],
                                set_name=card['set_name'],
                                year=card['year'],
                                condition=card.get('condition'),
                                player_name=card.get('player_name'),
                                card_number=card.get('card_number'),
                                card_variation=card.get('card_variation')
                            )
                            
                            # Prepare data for CSV
                            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            row_data = {
                                'timestamp': current_time,
                                'brand': card['brand'],
                                'set_name': card['set_name'],
                                'year': card['year'],
                                'condition': card.get('condition', 'N/A'),
                                'player_name': card.get('player_name', 'N/A'),
                                'card_number': card.get('card_number', 'N/A'),
                                'card_variation': card.get('card_variation', 'N/A'),
                                'predicted_price': str(price_data.predicted_price),
                                'confidence_score': str(price_data.confidence_score),
                                'recent_sales_count': str(len(price_data.recent_sales)),
                                'active_listings_count': str(len(price_data.active_listings)),
                                'market_trend': price_data.market_analysis.get('market_trend', 'unknown'),
                                'supply_level': price_data.market_analysis.get('supply_level', 'unknown'),
                                'price_trend': price_data.market_analysis.get('price_trend', 'unknown')
                            }
                            
                            # Write to CSV with lock
                            async with csv_lock:
                                file_exists = os.path.exists(output_csv_path)
                                with open(output_csv_path, 'a', newline='') as f:
                                    writer = csv.DictWriter(f, fieldnames=row_data.keys())
                                    if not file_exists:
                                        writer.writeheader()
                                    writer.writerow(row_data)
                            
                            results['successful'] += 1
                            return row_data
                            
                        except Exception as e:
                            results['failed'] += 1
                            results['errors'].append({
                                'card': card,
                                'error': str(e)
                            })
                            return None
                
                # Process all cards in the batch concurrently
                tasks = [process_card(card) for card in batch]
                loop.run_until_complete(asyncio.gather(*tasks))
                
            finally:
                # Close the event loop
                loop.close()
        
        return results
        
    except Exception as e:
        results['errors'].append({
            'error': str(e)
        })
        return results

# Add a new endpoint to process cards in parallel
@app.post("/process-cards-parallel", response_model=dict)
async def process_cards_parallel(
    input_csv_path: str,
    output_csv_path: str = 'card_prices.csv',
    max_concurrent: int = 5
):
    """
    Process multiple cards from an input CSV file in parallel and write results to an output CSV file.
    
    Args:
        input_csv_path (str): Path to the input CSV file containing card details
        output_csv_path (str): Path to write the results (default: 'card_prices.csv')
        max_concurrent (int): Maximum number of cards to process concurrently (default: 5)
    
    Returns:
        dict: Summary of processing results including success count and any errors
    """
    try:
        results = await process_cards_from_csv(input_csv_path, output_csv_path, max_concurrent)
        return results
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process cards: {str(e)}"
        )