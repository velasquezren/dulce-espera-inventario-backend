import paramiko

hostname = "107.172.193.34"
username = "root"
password = "java2025#"

# Let's inspect the current configuration files to see what Certbot wrote.
print("Connecting via SSH...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(hostname, username=username, password=password, timeout=15)
print("Connected!")

try:
    print("Reading /etc/httpd/conf.d/dulce_espera.conf...")
    stdin, stdout, stderr = ssh.exec_command("cat /etc/httpd/conf.d/dulce_espera.conf")
    conf_content = stdout.read().decode()
    print("CURRENT dulce_espera.conf:\n", conf_content)

    print("Checking for other files in /etc/httpd/conf.d/...")
    stdin, stdout, stderr = ssh.exec_command("ls -la /etc/httpd/conf.d/")
    ls_content = stdout.read().decode()
    print("FILES:\n", ls_content)

    # Let's see if dulce_espera-le-ssl.conf was created by Certbot
    if "dulce_espera-le-ssl.conf" in ls_content:
        print("Reading /etc/httpd/conf.d/dulce_espera-le-ssl.conf...")
        stdin, stdout, stderr = ssh.exec_command("cat /etc/httpd/conf.d/dulce_espera-le-ssl.conf")
        ssl_conf_content = stdout.read().decode()
        print("CURRENT SSL CONF:\n", ssl_conf_content)

finally:
    ssh.close()
