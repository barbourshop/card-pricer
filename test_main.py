import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from datetime import datetime, timedelta
from main import app

client = TestClient(app)

# Mock data for eBay API responses
MOCK_OAUTH_TOKEN = "mock_oauth_token"

MOCK_SALES_DATA = {
    "itemSummaries": [
        {
            "price": {"value": "150.00"},
            "soldDate": (datetime.utcnow() - timedelta(days=1)).isoformat(),
            "condition": "Near Mint"
        },
        {
            "price": {"value": "145.00"},
            "soldDate": (datetime.utcnow() - timedelta(days=30)).isoformat(),
            "condition": "Near Mint"
        },
        {
            "price": {"value": "160.00"},
            "soldDate": (datetime.utcnow() - timedelta(days=60)).isoformat(),
            "condition": "Mint"
        }
    ]
}

MOCK_ACTIVE_LISTINGS_DATA = {
    "itemSummaries": [
        {
            "price": {"value": "155.00"},
            "condition": "Near Mint",
            "buyingOptions": ["FIXED_PRICE"]
        },
        {
            "price": {"value": "165.00"},
            "condition": "Mint",
            "buyingOptions": ["FIXED_PRICE"]
        },
        {
            "price": {"value": "145.00"},
            "condition": "Near Mint",
            "buyingOptions": ["AUCTION"]
        }
    ]
}

@pytest.fixture
def mock_ebay_api():
    """Fixture to mock eBay API calls"""
    with patch("main.get_ebay_oauth_token") as mock_token, \
         patch("main.requests.get") as mock_get:
        
        # Mock OAuth token response
        mock_token.return_value = MOCK_OAUTH_TOKEN
        
        # Mock eBay API responses
        mock_sold_response = type('Response', (), {
            'status_code': 200,
            'json': lambda: MOCK_SALES_DATA
        })
        
        mock_active_response = type('Response', (), {
            'status_code': 200,
            'json': lambda: MOCK_ACTIVE_LISTINGS_DATA
        })
        
        # Set up the mock to return different responses based on the filter parameter
        def mock_get_side_effect(*args, **kwargs):
            params = kwargs.get('params', {})
            if 'soldItems' in params.get('filter', ''):
                return mock_sold_response
            else:
                return mock_active_response
        
        mock_get.side_effect = mock_get_side_effect
        
        yield

def test_get_card_price_basic(mock_ebay_api):
    """Test basic card price query with required parameters"""
    response = client.get("/card-price?brand=Topps&set=Chrome&year=2020")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "predicted_price" in data
    assert "confidence_score" in data
    assert "recent_sales" in data
    assert "active_listings" in data
    assert "market_analysis" in data
    assert len(data["recent_sales"]) == 3
    assert len(data["active_listings"]) == 3

def test_get_card_price_with_optional_params(mock_ebay_api):
    """Test card price query with all optional parameters"""
    response = client.get(
        "/card-price?brand=Topps&set=Chrome&year=2020"
        "&player_name=Mike Trout&card_number=1&card_variation=Refractor"
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["predicted_price"] > 0
    assert 0 <= data["confidence_score"] <= 1
    assert "market_analysis" in data

def test_get_card_price_missing_required_params():
    """Test card price query with missing required parameters"""
    response = client.get("/card-price?brand=Topps&set=Chrome")
    
    assert response.status_code == 422  # FastAPI validation error

def test_price_prediction_logic(mock_ebay_api):
    """Test that price prediction gives higher weight to recent sales"""
    response = client.get("/card-price?brand=Topps&set=Chrome&year=2020")
    data = response.json()
    
    # The predicted price should be closer to the most recent sale (150.00)
    # than to the oldest sale (160.00)
    assert abs(data["predicted_price"] - 150.00) < abs(data["predicted_price"] - 160.00)

def test_confidence_score_calculation(mock_ebay_api):
    """Test that confidence score is calculated correctly"""
    response = client.get("/card-price?brand=Topps&set=Chrome&year=2020")
    data = response.json()
    
    # With 3 sales and relatively consistent prices, confidence should be moderate
    assert 0.2 <= data["confidence_score"] <= 0.8

def test_market_analysis(mock_ebay_api):
    """Test that market analysis is calculated correctly"""
    response = client.get("/card-price?brand=Topps&set=Chrome&year=2020")
    data = response.json()
    
    market_analysis = data["market_analysis"]
    
    assert "market_trend" in market_analysis
    assert "supply_level" in market_analysis
    assert "price_trend" in market_analysis
    assert "avg_sale_price" in market_analysis
    assert "avg_active_price" in market_analysis
    assert "active_listings_count" in market_analysis
    assert "recent_sales_count" in market_analysis
    
    # Check that the values are reasonable
    assert market_analysis["active_listings_count"] == 3
    assert market_analysis["recent_sales_count"] == 3
    assert market_analysis["avg_sale_price"] > 0
    assert market_analysis["avg_active_price"] > 0

def test_active_listings_processing(mock_ebay_api):
    """Test that active listings are processed correctly"""
    response = client.get("/card-price?brand=Topps&set=Chrome&year=2020")
    data = response.json()
    
    active_listings = data["active_listings"]
    
    assert len(active_listings) == 3
    
    # Check that listing types are correctly identified
    buy_it_now_listings = [l for l in active_listings if l["listing_type"] == "buy_it_now"]
    auction_listings = [l for l in active_listings if l["listing_type"] == "auction"]
    
    assert len(buy_it_now_listings) == 2
    assert len(auction_listings) == 1 