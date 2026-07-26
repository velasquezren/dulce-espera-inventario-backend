import paramiko

hostname = "107.172.193.34"
username = "root"
password = "java2025#"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(hostname, username=username, password=password, timeout=15)

try:
    sftp = ssh.open_sftp()
    print("Uploading test script...")
    sftp.put("scratch/test_db_hosts.py", "/tmp/test_db_hosts.py")
    sftp.close()
    
    print("Running test script...")
    stdin, stdout, stderr = ssh.exec_command("/opt/dulce_espera_backend/venv/bin/python /tmp/test_db_hosts.py")
    print(stdout.read().decode())
    print(stderr.read().decode())
    
finally:
    ssh.close()
