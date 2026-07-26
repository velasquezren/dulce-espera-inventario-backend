from sqlalchemy import create_engine
import urllib.parse

# Test raw password url
url_raw = "mysql+pymysql://app_dulce_espera:DulceEsperaSecureApp2026!@127.0.0.1:3306/dulce_espera"
print(f"Testing raw URL: {url_raw}")
try:
    engine = create_engine(url_raw)
    conn = engine.connect()
    print("SUCCESS: Connected with raw URL!")
    conn.close()
except Exception as e:
    print(f"FAILED: Connected with raw URL: {e}")

# Test encoded password url
password_encoded = urllib.parse.quote_plus("DulceEsperaSecureApp2026!")
url_encoded = f"mysql+pymysql://app_dulce_espera:{password_encoded}@127.0.0.1:3306/dulce_espera"
print(f"\nTesting encoded URL: {url_encoded}")
try:
    engine = create_engine(url_encoded)
    conn = engine.connect()
    print("SUCCESS: Connected with encoded URL!")
    conn.close()
except Exception as e:
    print(f"FAILED: Connected with encoded URL: {e}")
