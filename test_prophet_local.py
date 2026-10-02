import sys
print("Loading Prophet...")
try:
    from prophet import Prophet
    print("Prophet loaded successfully.")
except Exception as e:
    print(f"Error loading Prophet: {e}")
    sys.exit(1)

import pandas as pd
print("Loading data...")
try:
    df = pd.DataFrame({
        'ds': pd.date_range(start='2023-01-01', periods=100, freq='D'),
        'y': range(100)
    })
    print("Data loaded.")
except Exception as e:
    print(f"Error data: {e}")

print("Fitting model...")
try:
    m = Prophet()
    m.fit(df)
    print("Model fitted successfully!")
except Exception as e:
    print(f"Error fitting: {e}")
