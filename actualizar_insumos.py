"""
Actualiza el catalogo de insumos desde el archivo que mantiene FileMaker.

Nunca borra ni vacia nada:
- Solo escribe los campos que el archivo trae con valor.
- Solo toca las filas que de verdad cambian.
- No elimina insumos: los pedidos antiguos apuntan a ellos.

Sin argumentos muestra lo que haria. Con --aplicar lo hace.
"""

import json
import os
import sys
from datetime import datetime

import pymysql
from dotenv import load_dotenv

RAIZ = "/opt/dulce_espera_backend"
load_dotenv(f"{RAIZ}/.env")

APLICAR = "--aplicar" in sys.argv
CAMPOS = {"nombre": "nombre", "grupo": "grupo", "presentacion": "presentacion"}

conexion = pymysql.connect(
    host=os.getenv("DB_HOST", "127.0.0.1"),
    port=int(os.getenv("DB_PORT", 3306)),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME", "dulce_espera"),
    charset="utf8mb4",
    cursorclass=pymysql.cursors.DictCursor,
)

archivo = json.load(open(f"{RAIZ}/insumos_actualizados.json", encoding="utf-8"))
nuevos = {i["id_publico"]: i for i in archivo["insumos"]}

try:
    with conexion.cursor() as cur:
        cur.execute("SELECT id_publico, nombre, categoria, grupo, presentacion, activo FROM insumos")
        actuales = {f["id_publico"]: f for f in cur.fetchall()}

    sello = datetime.now().strftime("%Y%m%d_%H%M%S")
    respaldo = f"{RAIZ}/respaldo_insumos_{sello}.json"
    with open(respaldo, "w", encoding="utf-8") as f:
        json.dump(list(actuales.values()), f, ensure_ascii=False, indent=1, default=str)
    print(f"Respaldo de {len(actuales)} insumos en {respaldo}\n")

    cambios, desconocidos = [], []
    for id_publico, nuevo in nuevos.items():
        actual = actuales.get(id_publico)
        if actual is None:
            desconocidos.append(id_publico)
            continue
        diferencias = {}
        for origen, columna in CAMPOS.items():
            valor = nuevo.get(origen)
            if valor and valor != (actual.get(columna) or ""):
                diferencias[columna] = valor
        if diferencias:
            cambios.append((id_publico, actual, diferencias))

    print(f"Insumos en el archivo : {len(nuevos)}")
    print(f"Insumos en la base    : {len(actuales)}")
    print(f"Filas a modificar     : {len(cambios)}")
    print(f"Ids del archivo que no existen en la base: {len(desconocidos)}")
    if desconocidos:
        print("  ", desconocidos[:10])
    print()

    for id_publico, actual, diferencias in cambios:
        print(f"  {id_publico:<8} {str(actual['nombre'])[:26]:<28}")
        for columna, valor in diferencias.items():
            print(f"             {columna:<13} {str(actual.get(columna))[:28]:<30} -> {valor}")

    if not APLICAR:
        print("\n(simulacion: no se escribio nada. Agregue --aplicar para ejecutarlo)")
        sys.exit(0)

    with conexion.cursor() as cur:
        for id_publico, _, diferencias in cambios:
            asignaciones = ", ".join(f"{c} = %s" for c in diferencias)
            cur.execute(
                f"UPDATE insumos SET {asignaciones}, fecha_actualizacion = %s WHERE id_publico = %s",
                [*diferencias.values(), datetime.now(), id_publico],
            )
    conexion.commit()
    print(f"\nListo: {len(cambios)} insumos actualizados.")

except Exception as error:
    conexion.rollback()
    print("Error, no se modifico nada:", error)
    raise
finally:
    conexion.close()
