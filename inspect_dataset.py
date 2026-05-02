import sys
import subprocess

def install_and_run():
    # Install pandas and openpyxl
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--user', 'pandas', 'openpyxl'])
    
    import pandas as pd
    import json
    
    # Read Biology as it's the biggest, so it likely has a solid schema
    df = pd.read_excel('c:/Users/Rekha/OneDrive/Desktop/Dataset-LuminaAI-20260502T121105Z-3-001/Dataset-LuminaAI/NEET-Biology.xlsx')
    
    print("Columns:", df.columns.tolist())
    print("First row data:")
    first_row = df.iloc[0].to_dict()
    print(json.dumps(first_row, default=str, indent=2))
    
    print("\nShape:", df.shape)

if __name__ == "__main__":
    install_and_run()
