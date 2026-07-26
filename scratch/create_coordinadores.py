import paramiko

hostname = "107.172.193.34"
username = "root"
password = "java2025#"

# SQL to create and seed the coordinadores table
sql_queries = (
    "CREATE TABLE IF NOT EXISTS dulce_espera.coordinadores ("
    "  id INT AUTO_INCREMENT PRIMARY KEY,"
    "  nombre VARCHAR(100) NOT NULL,"
    "  telefono VARCHAR(20) NOT NULL,"
    "  activo TINYINT DEFAULT 1"
    ");"
    # Seed coordinators
    "INSERT INTO dulce_espera.coordinadores (nombre, telefono, activo) VALUES "
    "('Nutrióloga Mariana Ríos', '593987654321', 1),"
    "('Chef Teresa Ortiz', '593912345678', 1),"
    "('Administración Dulce Espera', '593900000000', 1)"
    "ON DUPLICATE KEY UPDATE nombre=VALUES(nombre), telefono=VALUES(telefono);"
)

print("Connecting to remote server via SSH...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(hostname, username=username, password=password, timeout=15)
print("Connected!")

try:
    print("Creating and seeding coordinadores table...")
    cmd = f'mysql -u root -proot2020 -e "{sql_queries}"'
    stdin, stdout, stderr = ssh.exec_command(cmd)
    
    out = stdout.read().decode()
    err = stderr.read().decode()
    
    if out:
        print("STDOUT:", out)
    if err and "Warning" not in err:
        print("STDERR:", err)
        
    print("Verifying table data...")
    stdin, stdout, stderr = ssh.exec_command('mysql -u root -proot2020 -e "SELECT * FROM dulce_espera.coordinadores;"')
    print(stdout.read().decode())

finally:
    ssh.close()
