import paramiko

hostname = "107.172.193.34"
username = "root"
password = "java2025#"

commands = {
    "OS Version": "cat /etc/os-release | grep -E '^(NAME|VERSION)='",
    "Running Web Servers": "ss -tulpn | grep -E ':(80|443) '",
    "Web Server Process Details": "ps aux | grep -E '(nginx|apache2|httpd)' | grep -v grep",
    "Nginx Version": "nginx -v",
    "Apache Version": "apache2 -v || httpd -v",
    "Python version": "python3 --version",
    "Certbot installed": "certbot --version"
}

print("Connecting to remote server via SSH...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    ssh.connect(hostname, username=username, password=password, timeout=10)
    print("SSH Connection successful!\n")

    for name, cmd in commands.items():
        print(f"=== {name} ({cmd}) ===")
        stdin, stdout, stderr = ssh.exec_command(cmd)
        out = stdout.read().decode().strip()
        err = stderr.read().decode().strip()
        if out:
            print(out)
        if err:
            print(f"Error/Stderr: {err}")
        print()

finally:
    ssh.close()
