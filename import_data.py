import kagglehub
import os
import pandas as pd

# Ensure the /data folder exists
data_dir = os.path.join(os.getcwd(), "data")
os.makedirs(data_dir, exist_ok=True)

# Download the dataset from Kaggle
path = kagglehub.dataset_download("mkechinov/ecommerce-behavior-data-from-multi-category-store")
print(f"Dataset downloaded and extracted to: {path}")

# Find all CSV files in the extracted directory
csv_files = [os.path.join(path, f) for f in os.listdir(path) if f.endswith('.csv')]

# Convert each CSV file to a Parquet file in /data
for csv_file in csv_files:
    df = pd.read_csv(csv_file)
    parquet_file = os.path.join(data_dir, os.path.basename(csv_file).replace('.csv', '.parquet'))
    df.to_parquet(parquet_file, index=False)
    print(f"Converted {csv_file} to {parquet_file}")

print("All CSVs converted to Parquet in the /data folder!")
