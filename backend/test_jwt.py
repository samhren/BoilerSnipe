from jose import jwt, JWTError
from datetime import datetime, timedelta

SECRET_KEY = "your-super-secret-key-change-this-in-production"
ALGORITHM = "HS256"

# The token from the curl request
token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOjIsImV4cCI6MTc2NzE1NDMxMX0.PVa_iILD3xauQZzNN_IGWhNascPcm4HyfEiqAwkfUcA"

try:
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    print("✅ Token decoded successfully!")
    print(f"Payload: {payload}")
    print(f"User ID (sub): {payload.get('sub')}")
except JWTError as e:
    print(f"❌ JWT Error: {e}")
    print(f"Error type: {type(e)}")
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    print(f"Error type: {type(e)}")
