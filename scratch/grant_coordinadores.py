import paramiko

hostname = "107.172.193.34"
username = "root"
password = "java2025#"

# Grant SELECT permission on dulce_espera.coordinadores to our app user
sql_cmd = (
    "GRANT SELECT ON dulce_espera.coordinadores TO 'app_dulce_espera'@'%';"
    "FLUSH PRIVILEGES;"
)

print("Connecting to remote server via SSH...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(hostname, username=username, password=password, timeout=15)
print("Connected!")

try:
    print("Granting SELECT privilege on coordinadores table...")
    cmd = f'mysql -u root -proot2020 -e "{sql_cmd}"'
    stdin, stdout, stderr = ssh.exec_command(cmd)
    
    out = stdout.read().decode()
    err = stderr.read().decode()
    
    if out:
        print("STDOUT:", out)
    if err and "Warning" not in err:
        print("STDERR:", err)
        
    print("Permissions updated successfully!")

finally:
    ssh.close()
