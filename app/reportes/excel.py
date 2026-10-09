"""
Generadores de Excel (.xlsx) con openpyxl.

Se trasladaron tal cual desde main.py: son planillas que la gobernanta ya usa y
cambiarlas aqui no aporta nada. Lo que cambia es donde viven.
"""

from datetime import datetime
from typing import TYPE_CHECKING

# El canal lo resuelve el mismo criterio que usa el PDF.
from app.reportes.canales import de_linea as resolver_canal_compra

if TYPE_CHECKING:  # solo para los tipos: generar un documento no toca la base
    from app import models


def generar_excel_pedido(pedido: "models.Pedido"):
    import io
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Consolidado Compras"
    ws.views.sheetView[0].showGridLines = True

    TEAL_PRIMARY = "006156"
    DARK_TEXT = "0F172A"
    MUTED_TEXT = "64748B"
    BORDER_GRAY = "CBD5E1"

    font_banner = Font(name="Segoe UI", size=15, bold=True, color="FFFFFF")
    font_sub = Font(name="Segoe UI", size=9, bold=True, color="E2E8F0")
    font_lbl = Font(name="Segoe UI", size=9, bold=True, color=MUTED_TEXT)
    font_val = Font(name="Segoe UI", size=10, bold=True, color=DARK_TEXT)

    thin_border = Side(border_style="thin", color=BORDER_GRAY)
    border_cell = Border(left=thin_border, right=thin_border, top=thin_border, bottom=thin_border)

    # 1. Encabezado Institucional
    ws.merge_cells("A1:H1")
    ws["A1"] = "CLÍNICA MONTALVO — DULCE ESPERA"
    ws["A1"].font = font_banner
    ws["A1"].fill = PatternFill(start_color=TEAL_PRIMARY, end_color=TEAL_PRIMARY, fill_type="solid")
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 28

    ws.merge_cells("A2:H2")
    ws["A2"] = "ORDEN OFICIAL DE COMPRAS Y CONTROL DE SUMINISTROS"
    ws["A2"].font = font_sub
    ws["A2"].fill = PatternFill(start_color=TEAL_PRIMARY, end_color=TEAL_PRIMARY, fill_type="solid")
    ws["A2"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[2].height = 18

    # 2. Metadatos
    fecha_str = pedido.fecha_solicitud.strftime("%Y-%m-%d %H:%M") if pedido.fecha_solicitud else "N/A"
    id_ped = f"#{pedido.id_publico[:8].upper()}" if pedido.id_publico else f"#{pedido.id}"

    ws["A4"] = "PEDIDO N°:"; ws["A4"].font = font_lbl
    ws["B4"] = id_ped; ws["B4"].font = font_val
    ws["C4"] = "FECHA:"; ws["C4"].font = font_lbl
    ws["D4"] = fecha_str; ws["D4"].font = font_val
    ws["E4"] = "SOLICITADO POR:"; ws["E4"].font = font_lbl
    ws["F4"] = pedido.solicitante or "N/A"; ws["F4"].font = font_val
    ws["G4"] = "ESTADO:"; ws["G4"].font = font_lbl
    ws["H4"] = (pedido.estado or "Pendiente").upper(); ws["H4"].font = font_val

    row_cursor = 5
    if pedido.motivo:
        ws[f"A{row_cursor}"] = "JUSTIFICACIÓN:"; ws[f"A{row_cursor}"].font = font_lbl
        ws.merge_cells(f"B{row_cursor}:H{row_cursor}")
        ws[f"B{row_cursor}"] = f'"{pedido.motivo}"'
        ws[f"B{row_cursor}"].font = Font(name="Segoe UI", size=10, italic=True, color="334155")
        ws.row_dimensions[row_cursor].height = 18
        row_cursor += 1

    # Agrupación por canal
    lineas_mercado = []
    lineas_super = []
    lineas_prov = []
    lineas_otros = []

    for linea in pedido.lineas:
        item_data = {
            "nombre": linea.insumo.nombre if linea.insumo else "Insumo sin nombre",
            "presentacion": linea.insumo.presentacion if linea.insumo else "Unidades",
            "categoria": linea.insumo.categoria if linea.insumo else "Otros",
            "cantidad": float(linea.cantidad) if linea.cantidad else 0.0,
            "id_insumo": linea.insumo_id_publico or "N/A"
        }
        canal = resolver_canal_compra(linea)
        if canal == "Mercado":
            lineas_mercado.append(item_data)
        elif canal == "Super Mercado":
            lineas_super.append(item_data)
        elif canal == "Proveedor":
            lineas_prov.append(item_data)
        else:
            lineas_otros.append(item_data)

    # 3. KPI Resumen
    row_kpi_lbl = row_cursor + 1
    row_kpi_val = row_kpi_lbl + 1

    kpis = [
        ("TOTAL LÍNEAS", str(len(pedido.lineas)), "A", "B"),
        ("MERCADO", str(len(lineas_mercado)), "C", "D"),
        ("SUPERMERCADO", str(len(lineas_super)), "E", "F"),
        ("PROVEEDORES", str(len(lineas_prov)), "G", "H")
    ]
    fill_kpi = PatternFill(start_color="E6F0EF", end_color="E6F0EF", fill_type="solid")
    font_kpi_lbl = Font(name="Segoe UI", size=8, bold=True, color="475569")
    font_kpi_num = Font(name="Segoe UI", size=13, bold=True, color=TEAL_PRIMARY)

    for label, val, c1, c2 in kpis:
        ws.merge_cells(f"{c1}{row_kpi_lbl}:{c2}{row_kpi_lbl}")
        ws.merge_cells(f"{c1}{row_kpi_val}:{c2}{row_kpi_val}")
        c_lbl = ws[f"{c1}{row_kpi_lbl}"]
        c_lbl.value = label
        c_lbl.font = font_kpi_lbl
        c_lbl.alignment = Alignment(horizontal="center", vertical="center")
        c_lbl.fill = fill_kpi

        c_v = ws[f"{c1}{row_kpi_val}"]
        c_v.value = val
        c_v.font = font_kpi_num
        c_v.alignment = Alignment(horizontal="center", vertical="center")
        c_v.fill = fill_kpi

    ws.row_dimensions[row_kpi_lbl].height = 16
    ws.row_dimensions[row_kpi_val].height = 22

    col_widths = {"A": 6, "B": 38, "C": 20, "D": 15, "E": 14, "F": 14, "G": 16, "H": 28}
    for col, width in col_widths.items():
        ws.column_dimensions[col].width = width

    current_row = row_kpi_val + 2

    def escribir_tabla_canal(hoja, start_r, titulo, subtitulo, color_hex, lineas):
        hoja.merge_cells(f"A{start_r}:H{start_r}")
        c_sec = hoja[f"A{start_r}"]
        c_sec.value = f"{titulo.upper()} — {subtitulo}"
        c_sec.font = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")
        c_sec.fill = PatternFill(start_color=color_hex, end_color=color_hex, fill_type="solid")
        c_sec.alignment = Alignment(horizontal="left", vertical="center", indent=1)
        hoja.row_dimensions[start_r].height = 24

        th_r = start_r + 1
        headers = [
            ("A", "N°", Alignment(horizontal="center")),
            ("B", "Descripción del Insumo", Alignment(horizontal="left")),
            ("C", "Categoría", Alignment(horizontal="left")),
            ("D", "Cant. Solicitada", Alignment(horizontal="right")),
            ("E", "Unidad", Alignment(horizontal="center")),
            ("F", "Verificación [✓]", Alignment(horizontal="center")),
            ("G", "Cant. Recibida Real", Alignment(horizontal="right")),
            ("H", "Observaciones / Novedades", Alignment(horizontal="left"))
        ]
        for col, title, align in headers:
            c = hoja[f"{col}{th_r}"]
            c.value = title
            c.font = Font(name="Segoe UI", size=9, bold=True, color="FFFFFF")
            c.fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
            c.alignment = align
            c.border = border_cell
        hoja.row_dimensions[th_r].height = 20

        r_cursor = th_r + 1
        if not lineas:
            hoja.merge_cells(f"A{r_cursor}:H{r_cursor}")
            empty_c = hoja[f"A{r_cursor}"]
            empty_c.value = f"No se registraron requerimientos para {titulo}."
            empty_c.font = Font(name="Segoe UI", size=9, italic=True, color="64748B")
            empty_c.alignment = Alignment(horizontal="center", vertical="center")
            for col in ["A", "B", "C", "D", "E", "F", "G", "H"]:
                hoja[f"{col}{r_cursor}"].border = border_cell
            return r_cursor + 2

        lineas_ordenadas = sorted(lineas, key=lambda x: (x["categoria"] or "", x["nombre"] or ""))
        for idx, item in enumerate(lineas_ordenadas, 1):
            is_zebra = (idx % 2 == 0)
            row_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid") if is_zebra else None

            hoja[f"A{r_cursor}"].value = idx
            hoja[f"A{r_cursor}"].alignment = Alignment(horizontal="center")
            hoja[f"A{r_cursor}"].font = Font(name="Segoe UI", size=9, color="64748B", bold=True)

            hoja[f"B{r_cursor}"].value = item["nombre"]
            hoja[f"B{r_cursor}"].alignment = Alignment(horizontal="left")
            hoja[f"B{r_cursor}"].font = Font(name="Segoe UI", size=10, color="0F172A", bold=True)

            hoja[f"C{r_cursor}"].value = item["categoria"]
            hoja[f"C{r_cursor}"].alignment = Alignment(horizontal="left")
            hoja[f"C{r_cursor}"].font = Font(name="Segoe UI", size=9, color="475569")

            hoja[f"D{r_cursor}"].value = item["cantidad"]
            hoja[f"D{r_cursor}"].number_format = "#,##0.00"
            hoja[f"D{r_cursor}"].alignment = Alignment(horizontal="right")
            hoja[f"D{r_cursor}"].font = Font(name="Segoe UI", size=10, bold=True, color="006156")

            hoja[f"E{r_cursor}"].value = item["presentacion"]
            hoja[f"E{r_cursor}"].alignment = Alignment(horizontal="center")
            hoja[f"E{r_cursor}"].font = Font(name="Segoe UI", size=9, color="475569")

            hoja[f"F{r_cursor}"].value = ""
            hoja[f"F{r_cursor}"].alignment = Alignment(horizontal="center")

            hoja[f"G{r_cursor}"].value = ""
            hoja[f"G{r_cursor}"].number_format = "#,##0.00"
            hoja[f"G{r_cursor}"].alignment = Alignment(horizontal="right")

            hoja[f"H{r_cursor}"].value = ""
            hoja[f"H{r_cursor}"].alignment = Alignment(horizontal="left")

            for col in ["A", "B", "C", "D", "E", "F", "G", "H"]:
                cell = hoja[f"{col}{r_cursor}"]
                cell.border = border_cell
                if row_fill:
                    cell.fill = row_fill

            hoja.row_dimensions[r_cursor].height = 20
            r_cursor += 1

        # Fila de Subtotal
        hoja.merge_cells(f"A{r_cursor}:C{r_cursor}")
        hoja[f"A{r_cursor}"].value = f"TOTAL {titulo.upper()}:"
        hoja[f"A{r_cursor}"].font = Font(name="Segoe UI", size=9, bold=True, color="0F172A")
        hoja[f"A{r_cursor}"].alignment = Alignment(horizontal="right")

        hoja[f"D{r_cursor}"].value = f"=SUM(D{th_r + 1}:D{r_cursor - 1})"
        hoja[f"D{r_cursor}"].number_format = "#,##0.00"
        hoja[f"D{r_cursor}"].font = Font(name="Segoe UI", size=10, bold=True, color="006156")
        hoja[f"D{r_cursor}"].alignment = Alignment(horizontal="right")

        for col in ["A", "B", "C", "D", "E", "F", "G", "H"]:
            c = hoja[f"{col}{r_cursor}"]
            c.border = Border(top=Side(border_style="thin", color="0F172A"), bottom=Side(border_style="medium", color="0F172A"))
            c.fill = PatternFill(start_color="E2E8F0", end_color="E2E8F0", fill_type="solid")

        hoja.row_dimensions[r_cursor].height = 22
        return r_cursor + 2

    current_row = escribir_tabla_canal(ws, current_row, "Plaza de Mercado", "Perecederos, Carnes, Frutas y Verduras frescas", "B45309", lineas_mercado)
    current_row = escribir_tabla_canal(ws, current_row, "Supermercado y Abarrotes", "Secos, Lácteos industriales, Granos y Limpieza", "006156", lineas_super)
    current_row = escribir_tabla_canal(ws, current_row, "Proveedores Directos", "Distribuidoras, Panadería, Kéfir y Especiales", "4338CA", lineas_prov)
    if lineas_otros:
        current_row = escribir_tabla_canal(ws, current_row, "Otros Insumos y Servicios", "Descartables, envases y consumos varios", "475569", lineas_otros)

    # Firmas institucionales
    current_row += 1
    ws.merge_cells(f"A{current_row}:C{current_row}")
    ws[f"A{current_row}"].value = "____________________________________"
    ws[f"A{current_row}"].alignment = Alignment(horizontal="center")

    ws.merge_cells(f"E{current_row}:G{current_row}")
    ws[f"E{current_row}"].value = "____________________________________"
    ws[f"E{current_row}"].alignment = Alignment(horizontal="center")
    current_row += 1

    ws.merge_cells(f"A{current_row}:C{current_row}")
    ws[f"A{current_row}"].value = "Firma Solicitante Cocina"
    ws[f"A{current_row}"].font = Font(name="Segoe UI", size=9, bold=True, color="475569")
    ws[f"A{current_row}"].alignment = Alignment(horizontal="center")

    ws.merge_cells(f"E{current_row}:G{current_row}")
    ws[f"E{current_row}"].value = "Firma Gobernanta / Control de Suministros"
    ws[f"E{current_row}"].font = Font(name="Segoe UI", size=9, bold=True, color="475569")
    ws[f"E{current_row}"].alignment = Alignment(horizontal="center")

    # Guardar en memoria
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def generar_excel_pendientes(pedidos):
    """Consolidado maestro de los pedidos recibidos, agrupado por canal."""
    import io
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Consolidado Pendientes"
    ws.views.sheetView[0].showGridLines = True

    TEAL_PRIMARY = "006156"
    BORDER_GRAY = "CBD5E1"
    thin_border = Side(border_style="thin", color=BORDER_GRAY)
    border_cell = Border(left=thin_border, right=thin_border, top=thin_border, bottom=thin_border)

    ws.merge_cells("A1:G1")
    ws["A1"] = "CLÍNICA MONTALVO — DULCE ESPERA"
    ws["A1"].font = Font(name="Segoe UI", size=15, bold=True, color="FFFFFF")
    ws["A1"].fill = PatternFill(start_color=TEAL_PRIMARY, end_color=TEAL_PRIMARY, fill_type="solid")
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 28

    ws.merge_cells("A2:G2")
    ws["A2"] = f"CONSOLIDADO MAESTRO DE COMPRAS PENDIENTES — {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    ws["A2"].font = Font(name="Segoe UI", size=9, bold=True, color="E2E8F0")
    ws["A2"].fill = PatternFill(start_color=TEAL_PRIMARY, end_color=TEAL_PRIMARY, fill_type="solid")
    ws["A2"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[2].height = 18

    # Consolidar insumos por canal acumulando cantidades
    canales_acum = {
        "Mercado": {},
        "Super Mercado": {},
        "Proveedor": {},
        "Otros": {}
    }
    for ped in pedidos:
        for lin in ped.lineas:
            c = resolver_canal_compra(lin)
            if c not in canales_acum:
                c = "Otros"
            ins_id = lin.insumo_id_publico or "sin_id"
            ins_nombre = lin.insumo.nombre if lin.insumo else "Insumo"
            ins_pres = lin.insumo.presentacion if lin.insumo else "Unidad"
            ins_cat = lin.insumo.categoria if lin.insumo else "Otros"
            cant = float(lin.cantidad) if lin.cantidad else 0.0

            if ins_id not in canales_acum[c]:
                canales_acum[c][ins_id] = {
                    "nombre": ins_nombre,
                    "categoria": ins_cat,
                    "presentacion": ins_pres,
                    "cantidad": 0.0,
                    "pedidos_count": 0
                }
            canales_acum[c][ins_id]["cantidad"] += cant
            canales_acum[c][ins_id]["pedidos_count"] += 1

    col_widths = {"A": 6, "B": 38, "C": 20, "D": 15, "E": 14, "F": 16, "G": 28}
    for col, width in col_widths.items():
        ws.column_dimensions[col].width = width

    current_r = 4
    for canal_name, color, sub in [
        ("Mercado", "B45309", "Perecederos, Carnes, Frutas y Verduras"),
        ("Super Mercado", "006156", "Secos, Granos, Lácteos y Abarrotes"),
        ("Proveedor", "4338CA", "Distribuidoras Especiales y Panadería"),
        ("Otros", "475569", "Consumos Varios y Descartables")
    ]:
        items_dict = canales_acum.get(canal_name, {})
        ws.merge_cells(f"A{current_r}:G{current_r}")
        ws[f"A{current_r}"].value = f"CANAL: {canal_name.upper()} — {sub}"
        ws[f"A{current_r}"].font = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")
        ws[f"A{current_r}"].fill = PatternFill(start_color=color, end_color=color, fill_type="solid")
        ws[f"A{current_r}"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
        ws.row_dimensions[current_r].height = 24
        current_r += 1

        th_r = current_r
        headers = [
            ("A", "N°", Alignment(horizontal="center")),
            ("B", "Descripción Insumo", Alignment(horizontal="left")),
            ("C", "Categoría", Alignment(horizontal="left")),
            ("D", "Cant. Total", Alignment(horizontal="right")),
            ("E", "Unidad", Alignment(horizontal="center")),
            ("F", "Solicitudes", Alignment(horizontal="center")),
            ("G", "Observaciones / Check", Alignment(horizontal="left"))
        ]
        for col, title, align in headers:
            c = ws[f"{col}{th_r}"]
            c.value = title
            c.font = Font(name="Segoe UI", size=9, bold=True, color="FFFFFF")
            c.fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
            c.alignment = align
            c.border = border_cell
        ws.row_dimensions[th_r].height = 20
        current_r += 1

        if not items_dict:
            ws.merge_cells(f"A{current_r}:G{current_r}")
            ws[f"A{current_r}"].value = f"No hay insumos pendientes para {canal_name}."
            ws[f"A{current_r}"].font = Font(name="Segoe UI", size=9, italic=True, color="64748B")
            ws[f"A{current_r}"].alignment = Alignment(horizontal="center")
            for col in ["A", "B", "C", "D", "E", "F", "G"]:
                ws[f"{col}{current_r}"].border = border_cell
            current_r += 2
            continue

        items_sorted = sorted(items_dict.values(), key=lambda x: (x["categoria"], x["nombre"]))
        for idx, it in enumerate(items_sorted, 1):
            is_zebra = (idx % 2 == 0)
            row_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid") if is_zebra else None

            ws[f"A{current_r}"].value = idx
            ws[f"A{current_r}"].alignment = Alignment(horizontal="center")
            ws[f"A{current_r}"].font = Font(name="Segoe UI", size=9, bold=True, color="64748B")

            ws[f"B{current_r}"].value = it["nombre"]
            ws[f"B{current_r}"].font = Font(name="Segoe UI", size=10, bold=True, color="0F172A")

            ws[f"C{current_r}"].value = it["categoria"]
            ws[f"C{current_r}"].font = Font(name="Segoe UI", size=9, color="475569")

            ws[f"D{current_r}"].value = it["cantidad"]
            ws[f"D{current_r}"].number_format = "#,##0.00"
            ws[f"D{current_r}"].alignment = Alignment(horizontal="right")
            ws[f"D{current_r}"].font = Font(name="Segoe UI", size=10, bold=True, color="006156")

            ws[f"E{current_r}"].value = it["presentacion"]
            ws[f"E{current_r}"].alignment = Alignment(horizontal="center")
            ws[f"E{current_r}"].font = Font(name="Segoe UI", size=9, color="475569")

            ws[f"F{current_r}"].value = f"{it['pedidos_count']} ped."
            ws[f"F{current_r}"].alignment = Alignment(horizontal="center")
            ws[f"F{current_r}"].font = Font(name="Segoe UI", size=9, color="64748B")

            ws[f"G{current_r}"].value = ""

            for col in ["A", "B", "C", "D", "E", "F", "G"]:
                c = ws[f"{col}{current_r}"]
                c.border = border_cell
                if row_fill:
                    c.fill = row_fill
            ws.row_dimensions[current_r].height = 20
            current_r += 1

        # Subtotal
        ws.merge_cells(f"A{current_r}:C{current_r}")
        ws[f"A{current_r}"].value = f"TOTAL {canal_name.upper()}:"
        ws[f"A{current_r}"].font = Font(name="Segoe UI", size=9, bold=True, color="0F172A")
        ws[f"A{current_r}"].alignment = Alignment(horizontal="right")

        ws[f"D{current_r}"].value = f"=SUM(D{th_r + 1}:D{current_r - 1})"
        ws[f"D{current_r}"].number_format = "#,##0.00"
        ws[f"D{current_r}"].font = Font(name="Segoe UI", size=10, bold=True, color="006156")
        ws[f"D{current_r}"].alignment = Alignment(horizontal="right")

        for col in ["A", "B", "C", "D", "E", "F", "G"]:
            c = ws[f"{col}{current_r}"]
            c.border = Border(top=Side(border_style="thin", color="0F172A"), bottom=Side(border_style="medium", color="0F172A"))
            c.fill = PatternFill(start_color="E2E8F0", end_color="E2E8F0", fill_type="solid")
        ws.row_dimensions[current_r].height = 22
        current_r += 2

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf
