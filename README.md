# Card Pricer API

This API helps predict the value of sports cards by analyzing recent eBay sales data.

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file with your eBay API credentials:
```
EBAY_APP_ID=your_app_id
EBAY_CERT_ID=your_cert_id
EBAY_DEV_ID=your_dev_id
```

4. Run the API:
```bash
uvicorn main:app --reload
```

## API Endpoints

### GET /card-price
Query parameters:
- brand (required): Card brand (e.g., Topps, Upper Deck)
- set (required): Card set name
- year (required): Card year
- player_name (optional): Player name
- card_number (optional): Card number
- card_variation (optional): Card variation

Example request:
```
GET /card-price?brand=Topps&set=Chrome&year=2020&player_name=Mike Trout&card_number=1
```

## Response Format
```json
{
    "predicted_price": 150.25,
    "confidence_score": 0.85,
    "recent_sales": [
        {
            "sale_date": "2023-10-15",
            "price": 145.00,
            "condition": "Near Mint"
        }
    ]
}
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
