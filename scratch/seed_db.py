import paramiko
import uuid

hostname = "107.172.193.34"
username = "root"
password = "java2025#"

# Sample insumos to insert
insumos_data = [
    {
        "id_publico": str(uuid.uuid4()),
        "nombre": "Fórmula Enteral Polimérica",
        "categoria": "Nutrición Clínica",
        "presentacion": "Latas de 400g"
    },
    {
        "id_publico": str(uuid.uuid4()),
        "nombre": "Leche Semidescremada",
        "categoria": "Lácteos",
        "presentacion": "Litros"
    },
    {
        "id_publico": str(uuid.uuid4()),
        "nombre": "Pechuga de Pollo",
        "categoria": "Carnes y Proteínas",
        "presentacion": "Kilogramos"
    },
    {
        "id_publico": str(uuid.uuid4()),
        "nombre": "Arroz Integral",
        "categoria": "Granos y Cereales",
        "presentacion": "Kilogramos"
    },
    {
        "id_publico": str(uuid.uuid4()),
        "nombre": "Aceite de Oliva Extra Virgen",
        "categoria": "Abarrotes",
        "presentacion": "Botellas de 1L"
    }
]

print("Connecting via SSH to remote server...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(hostname, username=username, password=password, timeout=15)
print("Connected!")

try:
    print("Clearing old test items to avoid primary key duplicates (if any)...")
    clear_cmd = 'mysql -u root -proot2020 -e "DELETE FROM dulce_espera.insumos;"'
    ssh.exec_command(clear_cmd)

    print("Inserting test insumos...")
    for item in insumos_data:
        sql = (
            f"INSERT INTO dulce_espera.insumos "
            f"(id_publico, nombre, categoria, presentacion, activo, fecha_actualizacion) "
            f"VALUES ('{item['id_publico']}', '{item['nombre']}', '{item['categoria']}', '{item['presentacion']}', 1, NOW());"
        )
        cmd = f'mysql -u root -proot2020 -e "{sql}"'
        stdin, stdout, stderr = ssh.exec_command(cmd)
        err = stderr.read().decode()
        if err and "Warning" not in err:
            print(f"Error inserting {item['nombre']}: {err}")
        else:
            print(f"Inserted: {item['nombre']} ({item['id_publico']})")

    # Verify counts
    stdin, stdout, stderr = ssh.exec_command('mysql -u root -proot2020 -e "SELECT COUNT(*) FROM dulce_espera.insumos;"')
    print("\nTotal insumos in DB now:")
    print(stdout.read().decode())

finally:
    ssh.close()
