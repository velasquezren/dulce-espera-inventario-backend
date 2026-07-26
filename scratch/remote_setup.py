import paramiko

hostname = "107.172.193.34"
username = "root"
password = "java2025#"

sql_commands = (
    "CREATE USER IF NOT EXISTS 'app_dulce_espera'@'%' IDENTIFIED BY 'DulceEsperaSecureApp2026!';"
    "GRANT SELECT ON dulce_espera.insumos TO 'app_dulce_espera'@'%';"
    "GRANT SELECT, INSERT, UPDATE ON dulce_espera.pedidos TO 'app_dulce_espera'@'%';"
    "GRANT SELECT, INSERT, UPDATE ON dulce_espera.detalle_pedido TO 'app_dulce_espera'@'%';"
    "FLUSH PRIVILEGES;"
)

mysql_cmd = f'mysql -u root -proot2020 -e "{sql_commands}"'

print("Connecting to remote server via SSH...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    ssh.connect(hostname, username=username, password=password, timeout=10)
    print("SSH Connection successful!")

    print("Running MySQL user configuration command...")
    stdin, stdout, stderr = ssh.exec_command(mysql_cmd)
    
    out_content = stdout.read().decode()
    err_content = stderr.read().decode()

    if out_content:
        print("STDOUT:")
        print(out_content)
    if err_content:
        print("STDERR:")
        print(err_content)
        
    print("MySQL configuration step complete.")

    # Let's verify the user is created and can connect
    stdin, stdout, stderr = ssh.exec_command('mysql -u app_dulce_espera -p"DulceEsperaSecureApp2026!" -e "SHOW GRANTS;"')
    out_verify = stdout.read().decode()
    err_verify = stderr.read().decode()
    
    if out_verify:
        print("\nUser verification (SHOW GRANTS) SUCCESS:")
        print(out_verify)
    if err_verify:
        print("\nUser verification FAILED:")
        print(err_verify)

finally:
    ssh.close()
