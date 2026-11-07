"""
Actualiza el catalogo de insumos desde el archivo que mantiene FileMaker.

Nunca borra ni vacia nada:
- Solo escribe los campos que el archivo trae con valor.
- Solo toca las filas que de verdad cambian.
- No elimina insumos: los pedidos antiguos apuntan a ellos.

Sin argumentos muestra lo que haria. Con --aplicar lo hace.
Los insumos que el archivo trae y la base no tiene solo se crean si ademas
se pasa --crear, para que un id mal escrito no invente un insumo.
"""

import json
import os
import sys
import unicodedata
from datetime import datetime

import pymysql
from dotenv import load_dotenv

RAIZ = "/opt/dulce_espera_backend"
load_dotenv(f"{RAIZ}/.env")

APLICAR = "--aplicar" in sys.argv
CREAR = "--crear" in sys.argv
CAMPOS = {
    "nombre": "nombre",
    "grupo": "grupo",
    "presentacion": "presentacion",
    "categoria": "categoria",
}

conexion = pymysql.connect(
    host=os.getenv("DB_HOST", "127.0.0.1"),
    port=int(os.getenv("DB_PORT", 3306)),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME", "dulce_espera"),
    charset="utf8mb4",
    cursorclass=pymysql.cursors.DictCursor,
)

def sin_tildes(texto):
    descompuesto = unicodedata.normalize("NFD", (texto or "").strip().lower())
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")


def canonizar_categorias(nuevos, actuales):
    """
    Respeta como esta escrita cada categoria en la base.

    FileMaker a veces exporta "Dulceria" donde la base dice "Dulceria" con
    tilde. Si se escribieran las dos, la hoja de compras partiria una misma
    categoria en dos grupos. Una categoria que de verdad es nueva, o un
    nombre mal escrito que el archivo viene a corregir, no coinciden al
    quitar las tildes y pasan tal cual.
    """
    canonica = {}
    for fila in actuales.values():
        categoria = (fila.get("categoria") or "").strip()
        if categoria:
            canonica.setdefault(sin_tildes(categoria), categoria)

    ajustadas = 0
    for insumo in nuevos.values():
        entrante = (insumo.get("categoria") or "").strip()
        preferida = canonica.get(sin_tildes(entrante))
        if entrante and preferida and preferida != entrante:
            insumo["categoria"] = preferida
            ajustadas += 1
    return ajustadas


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

    ajustadas = canonizar_categorias(nuevos, actuales)
    if ajustadas:
        print(f"Categorias escritas como ya estaban en la base: {ajustadas}\n")

    cambios, por_crear = [], []
    for id_publico, nuevo in nuevos.items():
        actual = actuales.get(id_publico)
        if actual is None:
            if nuevo.get("nombre"):
                por_crear.append(nuevo)
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
    print(f"Insumos a crear       : {len(por_crear)}" + ("" if CREAR else "  (hacen falta --crear)"))
    print()

    for nuevo in por_crear:
        print(f"  NUEVO {nuevo['id_publico']:<8} {nuevo['nombre'][:30]:<32} "
              f"{nuevo.get('grupo') or '-':<14} {nuevo.get('categoria') or '-':<20} "
              f"{nuevo.get('presentacion') or '-'}")
    if por_crear:
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

        creados = 0
        if CREAR:
            for nuevo in por_crear:
                cur.execute(
                    "INSERT INTO insumos (id_publico, nombre, categoria, grupo, presentacion,"
                    " activo, fecha_actualizacion) VALUES (%s, %s, %s, %s, %s, 1, %s)",
                    [
                        nuevo["id_publico"],
                        nuevo["nombre"],
                        nuevo.get("categoria") or None,
                        nuevo.get("grupo") or None,
                        nuevo.get("presentacion") or None,
                        datetime.now(),
                    ],
                )
                creados += 1

    conexion.commit()
    print(f"\nListo: {len(cambios)} insumos actualizados" +
          (f" y {creados} creados." if CREAR else "."))

except Exception as error:
    conexion.rollback()
    print("Error, no se modifico nada:", error)
    raise
finally:
    conexion.close()
