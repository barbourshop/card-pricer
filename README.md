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
