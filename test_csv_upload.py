import asyncio
import time
import argparse
from main import process_cards_from_csv

async def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Process cards from CSV file')
    parser.add_argument('--input', type=str, default='card_inventory.csv', help='Input CSV file path')
    parser.add_argument('--output', type=str, default='card_prices.csv', help='Output CSV file path')
    parser.add_argument('--concurrent', type=int, default=5, help='Number of concurrent operations')
    parser.add_argument('--sequential', action='store_true', help='Run in sequential mode instead of parallel')
    args = parser.parse_args()
    
    print(f"Processing cards from {args.input} to {args.output}")
    
    # Record start time
    start_time = time.time()
    
    if args.sequential:
        print("Running in sequential mode...")
        # Call the original function with max_concurrent=1 to simulate sequential processing
        results = await process_cards_from_csv(args.input, args.output, max_concurrent=1)
    else:
        print(f"Running in parallel mode with {args.concurrent} concurrent operations...")
        # Call the function with the specified number of concurrent operations
        results = await process_cards_from_csv(args.input, args.output, max_concurrent=args.concurrent)
    
    # Calculate elapsed time
    elapsed_time = time.time() - start_time
    
    # Print results
    print(f"\nProcessing completed in {elapsed_time:.2f} seconds")
    print(f"Processed {results['total_cards']} cards")
    print(f"Successful: {results['successful']}")
    print(f"Failed: {results['failed']}")
    
    if results['errors']:
        print("Errors:")
        for error in results['errors']:
            print(f"  - {error}")

if __name__ == "__main__":
    # Create a new event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # Run the main function in the new event loop
        loop.run_until_complete(main())
    finally:
        # Close the event loop
        loop.close()