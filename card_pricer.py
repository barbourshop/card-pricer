import os
import csv
import asyncio
import time
import aiohttp
import base64
import numpy as np
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv
import argparse
import statistics
from urllib.parse import quote

# Load environment variables
load_dotenv()

# eBay API credentials
EBAY_APP_ID = os.getenv("EBAY_APP_ID")
EBAY_CERT_ID = os.getenv("EBAY_CERT_ID")
EBAY_DEV_ID = os.getenv("EBAY_DEV_ID")

# Keywords to exclude from listings
EXCLUDED_KEYWORDS = [
    "lot",
    "complete your set",
    "compete your set",
    "you pick",
    "you-pick",
    "you choose",
    "u pick",
    "pick your",
    "complete set",
    "bulk",
    "pick a card",
    "your pick",
    "pick from list",
    "pick from a list",
    "pyc",
    "pick your card",
    "select your card",
    "choose yours"
]

# Add token caching
_oauth_token = None
_token_expiry = None
_token_lock = None

# Rate limiter class
class RateLimiter:
    def __init__(self, calls_per_second):
        self.calls_per_second = calls_per_second
        self.last_call = 0
        self.lock = None
    
    async def acquire(self):
        if self.lock is None:
            self.lock = asyncio.Lock()
        
        async with self.lock:
            now = time.time()
            time_since_last_call = now - self.last_call
            if time_since_last_call < 1.0 / self.calls_per_second:
                await asyncio.sleep(1.0 / self.calls_per_second - time_since_last_call)
            self.last_call = time.time()

# Create global rate limiter
rate_limiter = RateLimiter(calls_per_second=2)

async def get_ebay_oauth_token():
    """Get eBay OAuth token with caching"""
    global _oauth_token, _token_expiry, _token_lock
    
    if _token_lock is None:
        _token_lock = asyncio.Lock()
    
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
                    raise Exception("Failed to get eBay OAuth token")
                
                response_data = await response.json()
                _oauth_token = response_data["access_token"]
                # Set token expiry to 1 hour before actual expiry to be safe
                _token_expiry = datetime.now() + timedelta(seconds=response_data["expires_in"] - 3600)
                return _oauth_token

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

def analyze_market(sales_data: List[Dict[str, Any]], active_listings: List[Dict[str, Any]]) -> Dict[str, Any]:
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

def predict_price(sales_data: List[Dict[str, Any]], active_listings: List[Dict[str, Any]]) -> Tuple[float, float]:
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

def filter_price_outliers(items: List[Dict[str, Any]], price_key: str = "price") -> List[Dict[str, Any]]:
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

def filter_by_title_keywords(items: List[Dict[str, Any]], title_key: str = "title", exclude_keywords: List[str] = None) -> List[Dict[str, Any]]:
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

async def get_card_price(brand, set_name, year, condition, player_name='', card_number='', card_variation='', session=None):
    """Get price data for a specific card from eBay."""
    try:
        # Get OAuth token
        oauth_token = await get_ebay_oauth_token()
        
        # Build search query - make it less strict
        search_query = f"{brand} {set_name} {year}"
        if player_name and len(player_name.strip()) > 0:
            search_query += f" {player_name}"
        if card_number and len(card_number.strip()) > 0:
            search_query += f" #{card_number}"
        if card_variation and len(card_variation.strip()) > 0:
            search_query += f" {card_variation}"
        
        print(f"Search query: {search_query}")
        
        # Calculate date range for last 90 days
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=90)
        
        # Format dates in ISO 8601 UTC format
        start_date_str = start_date.strftime('%Y-%m-%dT%H:%M:%S.000Z')
        end_date_str = end_date.strftime('%Y-%m-%dT%H:%M:%S.000Z')
        
        # Prepare eBay API request for sold items
        headers = {
            'Authorization': f'Bearer {oauth_token}',
            'Content-Type': 'application/json',
            'X-EBAY-C-MARKETPLACE-ID': 'EBAY_US'
        }
        
        # Build filter string - only filter by date range initially
        filter_string = f"soldItemsFilter:{{soldDateRange:{{startDate:'{start_date_str}',endDate:'{end_date_str}'}}}}"
        
        # Apply rate limiting
        await rate_limiter.acquire()
        
        # Make API call for sold items
        sold_items_url = f"https://api.ebay.com/buy/browse/v1/item_summary/search?q={quote(search_query)}&filter={quote(filter_string)}&limit=100"
        
        async with session.get(sold_items_url, headers=headers) as response:
            if response.status != 200:
                print(f"eBay API error: Status {response.status}")
                response_text = await response.text()
                print(f"Response: {response_text}")
                raise Exception(f"eBay API call failed with status {response.status}")
            
            response_json = await response.json()
            if not isinstance(response_json, dict):
                print(f"Unexpected response format: {response_json}")
                raise Exception("Invalid response format from eBay API")
            
            sold_items = response_json.get('itemSummaries', [])
            if not isinstance(sold_items, list):
                print(f"Invalid itemSummaries format: {sold_items}")
                raise Exception("Invalid itemSummaries format in eBay API response")
            
            print(f"\nFound {len(sold_items)} sold items before filtering")
            print("Initial sold items:")
            for item in sold_items:
                title = item.get('title', 'Unknown Title')
                price = item.get('price', {}).get('value', 0)
                condition_info = item.get('condition', {})
                condition_display = condition_info.get('conditionDisplayName', 'Unknown') if isinstance(condition_info, dict) else 'Unknown'
                print(f"  - {title} - ${price} - Condition: {condition_display}")
            
            # Process sold items with less strict filtering
            sales_data = []
            filtered_out = []
            for item in sold_items:
                if not isinstance(item, dict):
                    print(f"Invalid item format: {item}")
                    filtered_out.append(("Invalid format", item))
                    continue
                
                # Skip items with excluded keywords
                title = item.get('title', '').lower()
                if any(keyword in title for keyword in ['reprint', 'proxy', 'custom', 'lot', 'bulk']):
                    filtered_out.append(("Excluded keyword", title))
                    continue
                
                # Get sale date
                sale_date = item.get('itemEndDate') or item.get('soldDate')
                if not sale_date:
                    sale_date = datetime.now(timezone.utc).isoformat()
                
                # Get price safely
                price_info = item.get('price', {})
                if not isinstance(price_info, dict):
                    filtered_out.append(("Invalid price format", item))
                    continue
                
                try:
                    price = float(price_info.get('value', 0))
                except (ValueError, TypeError):
                    filtered_out.append(("Invalid price value", price_info))
                    continue
                
                if price > 0:  # Only include items with valid prices
                    # Get condition info with detailed logging
                    condition_info = item.get('condition', {})
                    condition_display = 'Unknown'
                    condition_id = 'Unknown'
                    
                    # Handle both dictionary and string condition formats
                    if isinstance(condition_info, dict):
                        condition_display = condition_info.get('conditionDisplayName', 'Unknown')
                        condition_id = condition_info.get('conditionId', 'Unknown')
                    elif isinstance(condition_info, str):
                        condition_display = condition_info
                        condition_id = condition_info
                    
                    print(f"Processing condition for {item.get('title')}:")
                    print(f"  - Display Name: {condition_display}")
                    print(f"  - Condition ID: {condition_id}")
                    
                    # Filter by condition if specified
                    if condition:
                        # Special handling for "Ungraded" and "Graded" conditions
                        if condition.lower() == "ungraded":
                            # For "Ungraded", allow any condition that doesn't contain "Graded" or is explicitly "Ungraded"
                            if "graded" in condition_display.lower() and "ungraded" not in condition_display.lower():
                                print(f"  - FILTERED: Condition mismatch - Expected: Ungraded, Got: {condition_display}")
                                filtered_out.append(("Condition mismatch", f"{item.get('title')} - Expected: Ungraded, Got: {condition_display}"))
                                continue
                            # If we get here, the condition is acceptable (either "Ungraded" or any other non-graded condition)
                            print(f"  - KEPT: Condition acceptable for Ungraded search: {condition_display}")
                        elif condition.lower() == "graded":
                            # For "Graded", only allow conditions containing "Graded"
                            if "graded" not in condition_display.lower():
                                print(f"  - FILTERED: Condition mismatch - Expected: Graded, Got: {condition_display}")
                                filtered_out.append(("Condition mismatch", f"{item.get('title')} - Expected: Graded, Got: {condition_display}"))
                                continue
                            # If we get here, the condition contains "Graded"
                            print(f"  - KEPT: Condition acceptable for Graded search: {condition_display}")
                        # For all other conditions, exact match required
                        elif condition.lower() != condition_display.lower():
                            print(f"  - FILTERED: Condition mismatch - Expected: {condition}, Got: {condition_display}")
                            filtered_out.append(("Condition mismatch", f"{item.get('title')} - Expected: {condition}, Got: {condition_display}"))
                            continue
                        else:
                            print(f"  - KEPT: Exact condition match: {condition_display}")
                    
                    # Extract just the numeric part of the item ID (between the first and second pipe)
                    item_id = item.get('itemId', '')
                    if '|' in item_id:
                        item_id = item_id.split('|')[1]  # Get the part between the first and second pipe
                    
                    sales_data.append({
                        'price': price,
                        'date': sale_date,
                        'condition': condition_display,
                        'condition_id': condition_id,
                        'title': item.get('title', ''),
                        'url': f"https://www.ebay.com/itm/{item_id}"  # Use the extracted numeric item ID
                    })
                else:
                    filtered_out.append(("Zero or negative price", price))
            
            print(f"\nAfter initial filtering:")
            print(f"  Kept: {len(sales_data)} sales")
            print(f"  Filtered out: {len(filtered_out)} items")
            print("\nFiltered out items:")
            for reason, item in filtered_out:
                print(f"  - {reason}: {item}")
            
            print("\nKept sales:")
            for sale in sales_data:
                print(f"  - {sale['title']} - ${sale['price']} - {sale['condition']}")
            
            # Filter out extreme price outliers (keep more data points)
            if sales_data and len(sales_data) > 2:
                prices = [sale['price'] for sale in sales_data]
                mean_price = statistics.mean(prices)
                std_dev = statistics.stdev(prices) if len(prices) > 1 else 0
                # Use 3 standard deviations instead of 2 to keep more data points
                outlier_threshold = 3 * std_dev
                print(f"\nPrice outlier filtering:")
                print(f"  Mean price: ${mean_price:.2f}")
                print(f"  Standard deviation: ${std_dev:.2f}")
                print(f"  Outlier threshold: ±${outlier_threshold:.2f}")
                
                filtered_sales = []
                for sale in sales_data:
                    if abs(sale['price'] - mean_price) <= outlier_threshold:
                        filtered_sales.append(sale)
                    else:
                        print(f"  - OUTLIER: {sale['title']} - ${sale['price']} (diff: ${abs(sale['price'] - mean_price):.2f})")
                
                sales_data = filtered_sales
                print(f"  After outlier filtering: {len(sales_data)} sales remaining")
            
            # Print remaining sales data
            print("\nRemaining sales data:")
            for sale in sales_data:
                print(f"  {sale.get('title', '')} - ${sale['price']} - {sale['condition']}")
            
            # Get active listings with less strict filtering
            # Use a completely different API endpoint for active listings
            # This ensures we get different results than the sold items
            
            # Apply rate limiting before making the API call
            await rate_limiter.acquire()
            
            # Make a separate API call for active listings with different parameters
            # Use the browse API with a different filter to get only active listings
            active_url = f"https://api.ebay.com/buy/browse/v1/item_summary/search"
            
            # Create a completely different query for active listings
            # Remove the -sold -completed flags as they might be causing issues
            # Also simplify the query to get more results
            active_query = search_query
            
            # Use different parameters for active listings
            active_params = {
                "q": active_query,
                "filter": "buyingOptions:{FIXED_PRICE|AUCTION}",
                "sort": "price",
                "limit": 100,
                "offset": 0
            }
            
            # Build the URL with query parameters
            active_url_with_params = f"{active_url}?q={quote(active_query)}&filter={quote('buyingOptions:{FIXED_PRICE|AUCTION}')}&sort=price&limit=100"
            
            print(f"Using active listings URL: {active_url_with_params}")
            
            async with session.get(active_url_with_params, headers=headers) as response:
                if response.status != 200:
                    response_text = await response.text()
                    print(f"eBay API error for active listings: Status {response.status}")
                    print(f"Response: {response_text}")
                    raise Exception(f"eBay API call for active listings failed with status {response.status}")
                
                active_data = await response.json()
                print(f"Number of active listings found: {len(active_data.get('itemSummaries', []))}")  # Debug log
                
                # Process active listings data
                active_listings = []
                for item in active_data.get("itemSummaries", []):
                    if "price" in item:
                        print(f"Found active listing: {item.get('title')} - ${item['price']['value']} - Condition: {item.get('condition', 'Unknown')}")  # Debug log
                        listing_type = "buy_it_now" if "FIXED_PRICE" in item.get("buyingOptions", []) else "auction"
                        
                        # Get condition info with detailed logging
                        condition_info = item.get("condition", {})
                        condition_display = 'Unknown'
                        
                        # Handle both dictionary and string condition formats
                        if isinstance(condition_info, dict):
                            condition_display = condition_info.get("conditionDisplayName", "Unknown")
                        elif isinstance(condition_info, str):
                            condition_display = condition_info
                        
                        print(f"Processing condition for {item.get('title')}:")
                        print(f"  - Display Name: {condition_display}")
                        
                        # Filter by condition if specified
                        if condition:
                            # Special handling for "Ungraded" and "Graded" conditions
                            if condition.lower() == "ungraded":
                                # For "Ungraded", allow any condition that doesn't contain "Graded" or is explicitly "Ungraded"
                                if "graded" in condition_display.lower() and "ungraded" not in condition_display.lower():
                                    print(f"  - FILTERED: Condition mismatch - Expected: Ungraded, Got: {condition_display}")
                                    continue
                                # If we get here, the condition is acceptable (either "Ungraded" or any other non-graded condition)
                                print(f"  - KEPT: Condition acceptable for Ungraded search: {condition_display}")
                            elif condition.lower() == "graded":
                                # For "Graded", only allow conditions containing "Graded"
                                if "graded" not in condition_display.lower():
                                    print(f"  - FILTERED: Condition mismatch - Expected: Graded, Got: {condition_display}")
                                    continue
                                # If we get here, the condition contains "Graded"
                                print(f"  - KEPT: Condition acceptable for Graded search: {condition_display}")
                            # For all other conditions, exact match required
                            elif condition.lower() != condition_display.lower():
                                print(f"  - FILTERED: Condition mismatch - Expected: {condition}, Got: {condition_display}")
                                continue
                            else:
                                print(f"  - KEPT: Exact condition match: {condition_display}")
                        
                        # Extract just the numeric part of the item ID (between the first and second pipe)
                        item_id = item.get('itemId', '')
                        if '|' in item_id:
                            item_id = item_id.split('|')[1]  # Get the part between the first and second pipe
                        
                        # Add the listing to active_listings
                        active_listings.append({
                            "price": float(item["price"]["value"]),
                            "condition": condition_display,
                            "listing_type": listing_type,
                            "title": item.get("title", ""),  # Add title to the active listings
                            "url": f"https://www.ebay.com/itm/{item_id}"  # Use the extracted numeric item ID
                        })
                        print(f"Added listing to active_listings: {active_listings[-1]}")  # Debug log
                
                print(f"Total active listings after processing: {len(active_listings)}")
                
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
                
                # Calculate market metrics
                if sales_data or active_listings:
                    # Perform market analysis
                    market_analysis = analyze_market(sales_data, active_listings)
                    
                    # Predict price based on available data
                    predicted_price = 0
                    confidence_score = 0
                    
                    if sales_data:
                        recent_prices = [sale['price'] for sale in sales_data]
                        predicted_price = statistics.mean(recent_prices)
                        confidence_score = min(1.0, len(sales_data) / 10.0)  # Scale confidence based on number of data points
                    elif active_listings:
                        active_prices = [listing['price'] for listing in active_listings]
                        predicted_price = statistics.mean(active_prices)
                        confidence_score = min(0.5, len(active_listings) / 20.0)  # Lower confidence for active-only
                else:
                    market_analysis = {
                        "market_trend": "unknown",
                        "supply_level": "unknown",
                        "price_trend": "unknown",
                        "avg_sale_price": 0,
                        "avg_active_price": 0,
                        "active_listings_count": 0,
                        "recent_sales_count": 0
                    }
                    predicted_price = 0
                    confidence_score = 0
                
                # Ensure active_listings and sales_data are distinct
                # Remove any active listings that are also in sales_data
                active_listings_filtered = []
                for listing in active_listings:
                    # Check if this listing is also in sales_data
                    is_duplicate = False
                    for sale in sales_data:
                        # Only consider it a duplicate if the title and price match EXACTLY
                        # This is a more strict check to avoid false positives
                        if (listing['title'].lower() == sale['title'].lower() and 
                            abs(listing['price'] - sale['price']) < 0.01):  # Allow for small price differences
                            is_duplicate = True
                            print(f"  - DUPLICATE: {listing['title']} - ${listing['price']} matches sale: {sale['title']} - ${sale['price']}")
                            break
                    
                    if not is_duplicate:
                        active_listings_filtered.append(listing)
                
                print(f"Active listings after removing duplicates: {len(active_listings_filtered)}")
                
                # If we filtered out all active listings, use the original list
                # This ensures we always have active listings to display
                if len(active_listings_filtered) == 0 and len(active_listings) > 0:
                    print("All active listings were considered duplicates. Using original list.")
                    active_listings_filtered = active_listings
                
                return {
                    'predicted_price': predicted_price,
                    'confidence_score': confidence_score,
                    'recent_sales': sales_data,
                    'active_listings': active_listings_filtered,
                    'market_analysis': market_analysis
                }
                
    except Exception as e:
        print(f"Error in get_card_price: {str(e)}")
        raise

async def process_cards_from_csv(input_csv_path, output_csv_path, max_concurrent=3):
    """Process multiple cards from an input CSV file and write results to an output CSV file."""
    results = {
        'total': 0,
        'successful': 0,
        'failed': 0,
        'errors': []
    }
    
    # Read the input CSV file
    with open(input_csv_path, 'r') as f:
        reader = csv.DictReader(f)
        cards = [row for row in reader]
    
    # Convert all values to strings and strip whitespace
    for card in cards:
        for key in card:
            card[key] = str(card[key]).strip()
    
    results['total'] = len(cards)
    
    # Create a semaphore to limit concurrent processes
    sem = asyncio.Semaphore(max_concurrent)
    
    # Create a lock for writing to the CSV file
    csv_lock = asyncio.Lock()
    
    # Create a single session for all requests
    async with aiohttp.ClientSession() as session:
        # Write header to output CSV
        with open(output_csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Card Name', 'Set', 'Year', 'Player Name', 'Card Number', 
                'Card Variation', 'Condition', 'Predicted Price', 'Confidence Score',
                'Recent Sales', 'Active Listings', 'Market Trend', 'Supply Level',
                'Price Trend', 'Average Sale Price', 'Average Active Price',
                'Active Listings Count', 'Recent Sales Count'
            ])
        
        async def process_card(card):
            async with sem:
                try:
                    # Get optional card attributes with defaults
                    player_name = card.get('player_name', '')
                    card_number = card.get('card_number', '')
                    card_variation = card.get('card_variation', '')
                    
                    # Get card price data
                    price_data = await get_card_price(
                        brand=card['brand'],
                        set_name=card['set_name'],
                        year=card['year'],
                        condition=card['condition'],
                        player_name=player_name,
                        card_number=card_number,
                        card_variation=card_variation,
                        session=session
                    )
                    
                    # Extract market analysis data
                    market_analysis = price_data['market_analysis']
                    
                    # Write results to output CSV
                    async with csv_lock:
                        with open(output_csv_path, 'a', newline='') as f:
                            writer = csv.writer(f)
                            writer.writerow([
                                f"{card['brand']} {card['set_name']} {card['year']}",
                                card['set_name'],
                                card['year'],
                                player_name,
                                card_number,
                                card_variation,
                                card['condition'],
                                price_data['predicted_price'],
                                price_data['confidence_score'],
                                len(price_data['recent_sales']),
                                len(price_data['active_listings']),
                                market_analysis['market_trend'],
                                market_analysis['supply_level'],
                                market_analysis['price_trend'],
                                market_analysis['avg_sale_price'],
                                market_analysis['avg_active_price'],
                                market_analysis['active_listings_count'],
                                market_analysis['recent_sales_count']
                            ])
                    
                    results['successful'] += 1
                    print(f"Successfully processed {card['brand']} {card['set_name']} {card['year']}")
                    
                except Exception as e:
                    results['failed'] += 1
                    error_msg = f"Error processing {card['brand']} {card['set_name']} {card['year']}: {str(e)}"
                    print(error_msg)
                    results['errors'].append({
                        'card': f"{card['brand']} {card['set_name']} {card['year']}",
                        'error': str(e)
                    })
        
        # Process all cards concurrently
        tasks = [process_card(card) for card in cards]
        await asyncio.gather(*tasks)
    
    # Print summary
    print("\nProcessing complete!")
    print(f"Total cards: {results['total']}")
    print(f"Successful: {results['successful']}")
    print(f"Failed: {results['failed']}")
    
    if results['errors']:
        print("\nErrors:")
        for error in results['errors']:
            print(f"  Card: {error['card']}")
            print(f"  Error: {error['error']}")
    
    print(f"\nResults have been written to {output_csv_path}")
    return results

def main():
    parser = argparse.ArgumentParser(description='Process cards from a CSV file and get price data.')
    parser.add_argument('--input', type=str, required=True, help='Path to the input CSV file')
    parser.add_argument('--output', type=str, default='card_prices.csv', help='Path to the output CSV file')
    parser.add_argument('--max-concurrent', type=int, default=3, help='Maximum number of concurrent processes')
    
    args = parser.parse_args()
    
    print("eBay Card Pricer - Batch Processing")
    print("===================================")
    print(f"Input file: {args.input}")
    print(f"Output file: {args.output}")
    print(f"Concurrent processing: {args.max_concurrent}")
    print("\nProcessing cards... This may take a while depending on the number of cards.")
    
    # Run the async function using asyncio
    results = asyncio.run(process_cards_from_csv(args.input, args.output, args.max_concurrent))
    
    print("\nProcessing complete!")
    print(f"Total cards: {results['total']}")
    print(f"Successful: {results['successful']}")
    print(f"Failed: {results['failed']}")
    
    if results['errors']:
        print("\nErrors encountered:")
        for error in results['errors']:
            print(f"- {error['card']}: {error['error']}")

if __name__ == "__main__":
    main() 