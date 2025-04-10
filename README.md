# Card Pricer API

A Python application that helps you price sports cards by analyzing recent eBay sales and active listings.

## Features

- Fetches recent sales data from eBay (last 90 days)
- Analyzes active listings on eBay
- Filters out irrelevant listings (lots, bulk sales, etc.)
- Removes price outliers for more accurate pricing
- Provides market analysis (trends, supply levels)
- Calculates a predicted price with confidence score
- Processes multiple cards in parallel for efficiency

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/ebay-card-pricer.git
   cd ebay-card-pricer
   ```

2. Create a virtual environment and activate it:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the project root with your eBay API credentials:
   ```
   EBAY_APP_ID=your_app_id
   EBAY_CERT_ID=your_cert_id
   EBAY_DEV_ID=your_dev_id
   ```

## Usage

### Processing a Single Card

You can use the `get_card_price` function to get pricing information for a single card:

```python
import asyncio
from card_pricer import get_card_price

async def main():
    result = await get_card_price(
        brand="Topps",
        set_name="Series 1",
        year="2023",
        player_name="Shohei Ohtani",
        card_number="100",
        condition="New"
    )
    
    print(f"Predicted Price: ${result['predicted_price']}")
    print(f"Confidence Score: {result['confidence_score']}")
    print(f"Market Trend: {result['market_analysis']['market_trend']}")
    print(f"Supply Level: {result['market_analysis']['supply_level']}")

asyncio.run(main())
```

## Price Prediction Algorithm

The API uses a sophisticated algorithm to predict card prices based on recent eBay sales data and active listings. Here's how it works:

### Data Collection
- Analyzes completed sales from the last 90 days
- Considers both auction and buy-it-now listings
- Filters out bulk lots, set completions, and other non-single card listings
- Removes statistical outliers using the Interquartile Range (IQR) method

### Price Prediction
The algorithm calculates the predicted price using:
1. Weighted average of recent sales (more recent sales have higher weight)
2. Weighted average of active listings (lower prices have higher weight)
3. Market trend adjustments based on two key factors:

   a. Price Trend (comparing active listings to recent sales):
   - "increasing": Active listings are 10% higher than recent sales
   - "decreasing": Active listings are 10% lower than recent sales
   - "stable": Active listings are within ±10% of recent sales

   b. Supply Level (comparing number of active listings to recent sales):
   - "high": More than 2x active listings compared to recent sales
   - "low": Less than 0.5x active listings compared to recent sales
   - "moderate": Between 0.5x and 2x active listings compared to recent sales

   The final market trend is determined by combining these factors:
   - "bullish": Increasing prices + low supply (indicating strong demand)
   - "bearish": Decreasing prices + high supply (indicating weak demand)
   - "neutral": All other combinations

   Price adjustments are then applied:
   - Bullish market: Increases prediction by 5%
   - Bearish market: Decreases prediction by 5%
   - Neutral market: Uses average of sales and listings

### Confidence Score
The confidence score (0.0 to 1.0) indicates how reliable the prediction is, based on:
- Number of recent sales (more sales = higher confidence)
- Number of active listings (more listings = higher confidence)
- Price consistency (less variance = higher confidence)
- Sales data is weighted 70% and active listings 30% in the final confidence calculation

### Market Analysis
The API provides market analysis including:
- Market Trend: "bullish", "bearish", or "neutral"
- Supply Level: "high", "moderate", or "low"
- Price Trend: "increasing", "decreasing", or "stable"
- Average sale price and active listing price
- Count of recent sales and active listings

This analysis helps understand the current market conditions and potential price movements. 
