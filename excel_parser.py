import pandas as pd


# Function to read the Excel file and extract relevant data
def read_excel(file):
    # Read the Excel file into a pandas dataframe
    df = pd.read_excel(file)

    # Assuming 'Project Number' and 'Project Name' columns exist in the sheet
    if 'Project Number' in df.columns and 'Project Name' in df.columns:
        return df
    else:
        raise ValueError("Excel file must contain 'Project Number' and 'Project Name' columns.")
