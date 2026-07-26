
import json
import pymysql
import os
from dotenv import load_dotenv

# Load env variables
load_dotenv("/opt/dulce_espera_backend/.env")

DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", 3306))
DB_USER = "root"
DB_PASSWORD = "root2020"
DB_NAME = os.getenv("DB_NAME", "dulce_espera")

print("Connecting to MySQL database...")
conn = pymysql.connect(
    host=DB_HOST,
    port=DB_PORT,
    user=DB_USER,
    password=DB_PASSWORD,
    database=DB_NAME,
    charset='utf8mb4',
    cursorclass=pymysql.cursors.DictCursor
)

try:
    with conn.cursor() as cursor:
        print("Disabling foreign key checks temporarily...")
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
        
        print("Clearing old tables...")
        cursor.execute("TRUNCATE TABLE detalle_pedido;")
        cursor.execute("TRUNCATE TABLE pedidos;")
        cursor.execute("TRUNCATE TABLE insumos;")
        
        print("Loading JSON data...")
        with open("/opt/dulce_espera_backend/insumos.json", "r", encoding="utf-8") as f:
            insumos = json.load(f)
            
        print(f"Loaded {len(insumos)} insumos from JSON.")
        
        insert_query = """
            INSERT INTO insumos (id_publico, nombre, categoria, grupo, presentacion, activo, fecha_actualizacion)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        
        records = []
        for item in insumos:
            records.append((
                item["id_publico"],
                item["nombre"],
                item["categoria"],
                item.get("grupo"),
                item["presentacion"],
                item["activo"],
                item["fecha_actualizacion"]
            ))
            
        print("Inserting records...")
        cursor.executemany(insert_query, records)
        
        print("Re-enabling foreign key checks...")
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
        
    conn.commit()
    print("Database population completed successfully!")
except Exception as e:
    conn.rollback()
    print("Error populating database:", e)
finally:
    conn.close()
