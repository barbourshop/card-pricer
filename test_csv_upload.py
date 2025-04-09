import asyncio
from main import process_cards_from_csv

async def main():
    results = await process_cards_from_csv('card_inventory.csv', 'card_prices.csv')
    print(f"Processed {results['total_cards']} cards")
    print(f"Successful: {results['successful']}")
    print(f"Failed: {results['failed']}")
    if results['errors']:
        print("Errors:")
        for error in results['errors']:
            print(f"  - {error}")

if __name__ == "__main__":
    asyncio.run(main())