import requests
import pandas as pd
import os

def upload_csv_to_api(csv_path):
    """Upload the CSV file to the API endpoint"""
    url = 'http://localhost:8000/process-cards-csv'
    
    # Open the file in binary mode
    with open(csv_path, 'rb') as f:
        files = {'file': ('card-prices.csv', f, 'text/csv')}
        response = requests.post(url, files=files)
    
    # Check if the request was successful
    if response.status_code == 200:
        # Save the response as a CSV file
        output_path = 'card_predictions.csv'
        with open(output_path, 'wb') as f:
            f.write(response.content)
        print(f"Success! Predictions saved to {output_path}")
        
        # Display the predictions
        predictions_df = pd.read_csv(output_path)
        print("\nPredictions:")
        print(predictions_df.to_string())
    else:
        print(f"Error: {response.status_code}")
        print(response.text)

def main():
    csv_path = 'card-prices.csv'
    
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found in the current directory")
        return
    
    print(f"Using existing CSV file: {csv_path}")
    
    # Upload to API
    print("\nUploading to API...")
    upload_csv_to_api(csv_path)

if __name__ == "__main__":
    main() 