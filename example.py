import asyncio
from card_pricer import get_card_price

async def main():
    """
    Example script demonstrating how to use the card pricer for a single card.
    """
    print("eBay Card Pricer - Single Card Example")
    print("=====================================")
    
    # Example card details
    brand = "Topps"
    set_name = "Series 1"
    year = "2023"
    player_name = "Shohei Ohtani"
    card_number = "100"
    condition = "New"
    
    print(f"\nLooking up price for: {brand} {set_name} {year} #{card_number} {player_name} ({condition})")
    print("This may take a minute...\n")
    
    try:
        # Get card price data
        result = await get_card_price(
            brand=brand,
            set_name=set_name,
            year=year,
            player_name=player_name,
            card_number=card_number,
            condition=condition
        )
        
        # Print results
        print("\nResults:")
        print(f"Predicted Price: ${result['predicted_price']:.2f}")
        print(f"Confidence Score: {result['confidence_score']:.2f}")
        
        print("\nMarket Analysis:")
        print(f"Market Trend: {result['market_analysis']['market_trend']}")
        print(f"Supply Level: {result['market_analysis']['supply_level']}")
        print(f"Price Trend: {result['market_analysis']['price_trend']}")
        print(f"Average Sale Price: ${result['market_analysis']['avg_sale_price']:.2f}")
        print(f"Average Active Price: ${result['market_analysis']['avg_active_price']:.2f}")
        
        print("\nData Points:")
        print(f"Recent Sales: {len(result['recent_sales'])}")
        print(f"Active Listings: {len(result['active_listings'])}")
        
        # Print recent sales
        if result['recent_sales']:
            print("\nRecent Sales:")
            for sale in result['recent_sales'][:5]:  # Show first 5 sales
                print(f"  ${sale['price']:.2f} - {sale['condition']} - {sale['sale_date'][:10]}")
            
            if len(result['recent_sales']) > 5:
                print(f"  ... and {len(result['recent_sales']) - 5} more sales")
        
        # Print active listings
        if result['active_listings']:
            print("\nActive Listings:")
            for listing in result['active_listings'][:5]:  # Show first 5 listings
                print(f"  ${listing['price']:.2f} - {listing['condition']} - {listing['listing_type']}")
            
            if len(result['active_listings']) > 5:
                print(f"  ... and {len(result['active_listings']) - 5} more listings")
    
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main()) 