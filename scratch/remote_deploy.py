import tarfile
import os
import io
import paramiko

# Remote server details
hostname = "107.172.193.34"
username = "root"
password = "java2025#"

# Configuration details
domain = "107.172.193.34.nip.io"
dest_dir = "/opt/dulce_espera_backend"

# Step 1: Create a local tarball of the backend application
tar_buf = io.BytesIO()
with tarfile.open(fileobj=tar_buf, mode="w:gz") as tar:
    # Add requirements.txt
    tar.add("requirements.txt", arcname="requirements.txt")
    # Add app directory
    tar.add("app", arcname="app")
    # Add .env.production as .env
    tar.add(".env.production", arcname=".env")

tar_buf.seek(0)
print("Tarball created in memory.")

# Connect to SSH
print(f"Connecting to {hostname} via SSH...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(hostname, username=username, password=password, timeout=15)
print("SSH Connection successful!")

try:
    # Step 2: Upload tarball using SFTP
    sftp = ssh.open_sftp()
    print("Uploading tarball...")
    sftp.putfo(tar_buf, "/tmp/backend.tar.gz")
    sftp.close()
    print("Upload complete!")

    # Step 3: Run commands to extract and configure
    cmds = [
        # Create destination directory
        f"mkdir -p {dest_dir}",
        # Extract files
        f"tar -xzf /tmp/backend.tar.gz -C {dest_dir}",
        # Install Python dependencies and system packages on AlmaLinux
        "dnf install -y python3-pip mod_ssl certbot python3-certbot-apache",
        # Create virtual environment
        f"python3 -m venv {dest_dir}/venv",
        # Upgrade pip and install requirements
        f"{dest_dir}/venv/bin/pip install --upgrade pip",
        f"{dest_dir}/venv/bin/pip install -r {dest_dir}/requirements.txt",
    ]

    for cmd in cmds:
        print(f"Running: {cmd}")
        stdin, stdout, stderr = ssh.exec_command(cmd)
        out = stdout.read().decode().strip()
        err = stderr.read().decode().strip()
        if out:
            print(out)
        if err:
            print(f"Error/Stderr: {err}")

    # Step 4: Write systemd service file on remote server
    service_content = f"""[Unit]
Description=Backend FastAPI - Dulce Espera
After=network.target

[Service]
User=root
WorkingDirectory={dest_dir}
Environment="PATH={dest_dir}/venv/bin"
ExecStart={dest_dir}/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 4
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
"""
    print("Writing Systemd service file...")
    sftp = ssh.open_sftp()
    with sftp.file("/etc/systemd/system/dulce_espera_backend.service", "w") as f:
        f.write(service_content)
    sftp.close()

    # Step 5: Write Apache virtual host file
    apache_content = f"""<VirtualHost *:80>
    ServerName {domain}

    ProxyPreserveHost On
    ProxyPass / http://127.0.0.1:8000/
    ProxyPassReverse / http://127.0.0.1:8000/

    ErrorLog /var/log/httpd/dulce_espera_error.log
    CustomLog /var/log/httpd/dulce_espera_access.log combined
</VirtualHost>
"""
    print("Writing Apache virtual host configuration...")
    sftp = ssh.open_sftp()
    with sftp.file("/etc/httpd/conf.d/dulce_espera.conf", "w") as f:
        f.write(apache_content)
    sftp.close()

    # Step 6: Reload daemon and start services
    post_cmds = [
        "systemctl daemon-reload",
        "systemctl enable dulce_espera_backend",
        "systemctl restart dulce_espera_backend",
        "systemctl restart httpd",
    ]

    for cmd in post_cmds:
        print(f"Running: {cmd}")
        stdin, stdout, stderr = ssh.exec_command(cmd)
        out = stdout.read().decode().strip()
        err = stderr.read().decode().strip()
        if out:
            print(out)
        if err:
            print(f"Error/Stderr: {err}")

    # Step 7: Run Certbot to configure HTTPS
    print("Running Certbot for SSL/HTTPS...")
    certbot_cmd = f"certbot --apache -d {domain} --non-interactive --agree-tos --email admin@644953.com"
    stdin, stdout, stderr = ssh.exec_command(certbot_cmd)
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    if out:
        print(out)
    if err:
        print(f"Certbot Stderr/Info: {err}")

    print("\nDEPLOYMENT COMPLETED SUCCESSFULLY!")

finally:
    ssh.close()
