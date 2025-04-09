import asyncio
import argparse
from card_pricer import process_cards_from_csv

async def main():
    """
    Script to process multiple cards from a CSV file.
    """
    parser = argparse.ArgumentParser(description='Process multiple cards from a CSV file')
    parser.add_argument('--input', type=str, default='sample_cards.csv', 
                        help='Path to input CSV file with card details (default: sample_cards.csv)')
    parser.add_argument('--output', type=str, default='card_prices.csv', 
                        help='Path to output CSV file (default: card_prices.csv)')
    parser.add_argument('--concurrent', type=int, default=3, 
                        help='Maximum number of cards to process concurrently (default: 3)')
    
    args = parser.parse_args()
    
    print("eBay Card Pricer - Batch Processing")
    print("===================================")
    print(f"Input file: {args.input}")
    print(f"Output file: {args.output}")
    print(f"Concurrent processing: {args.concurrent}")
    print("\nProcessing cards... This may take a while depending on the number of cards.\n")
    
    try:
        # Process cards from CSV
        results = await process_cards_from_csv(
            input_csv_path=args.input,
            output_csv_path=args.output,
            max_concurrent=args.concurrent
        )
        
        # Print results
        print("\nProcessing complete!")
        print(f"Total cards: {results['total_cards']}")
        print(f"Successful: {results['successful']}")
        print(f"Failed: {results['failed']}")
        
        if results['errors']:
            print("\nErrors:")
            for error in results['errors']:
                if 'card' in error:
                    print(f"  Card: {error['card']}")
                    print(f"  Error: {error['error']}")
                else:
                    print(f"  Error: {error['error']}")
        
        print(f"\nResults have been written to {args.output}")
    
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main()) 