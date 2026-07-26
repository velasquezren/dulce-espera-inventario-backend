import paramiko

hostname = "107.172.193.34"
username = "root"
password = "java2025#"

default_conf = """<VirtualHost *:80>
    DocumentRoot "/var/www/html"
</VirtualHost>
"""

print("Connecting via SSH...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(hostname, username=username, password=password, timeout=15)
print("Connected!")

try:
    print("Writing /etc/httpd/conf.d/00-default.conf...")
    sftp = ssh.open_sftp()
    with sftp.file("/etc/httpd/conf.d/00-default.conf", "w") as f:
        f.write(default_conf)
    sftp.close()
    print("File written successfully!")

    print("Restarting Apache (httpd)...")
    stdin, stdout, stderr = ssh.exec_command("systemctl restart httpd")
    print(stdout.read().decode())
    err = stderr.read().decode()
    if err:
        print("Error restarting Apache:", err)
    else:
        print("Apache restarted successfully!")

finally:
    ssh.close()
