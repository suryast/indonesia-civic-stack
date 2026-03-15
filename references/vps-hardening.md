# VPS Hardening for Indonesian Proxy Servers

> Lessons from setting up CloudKilat Jakarta as a SOCKS5 proxy for civic-stack.

## The Incident (2026-03-15)

Automated hardening script ran all security changes in one pass:
1. Created non-root user
2. Copied SSH key
3. Disabled root login
4. Disabled password auth
5. Disabled UsePAM
6. Enabled UFW
7. Installed fail2ban
8. Restarted sshd

**Result:** Locked out. The SSH key copy failed silently (home directory owned by root, account locked because `useradd` without `-p`), and password auth was already disabled.

Required 3 rounds of web console fixes to recover.

## The Correct Sequence

### Step 1: Create user and install key
```bash
useradd -m -s /bin/bash proxyuser
passwd proxyuser  # Set a real password
mkdir -p /home/proxyuser/.ssh
echo "ssh-ed25519 AAAA..." > /home/proxyuser/.ssh/authorized_keys
chown -R proxyuser:proxyuser /home/proxyuser  # Including home dir itself!
chmod 700 /home/proxyuser/.ssh
chmod 600 /home/proxyuser/.ssh/authorized_keys
echo "proxyuser ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/proxyuser
```

### Step 2: VERIFY key login in a separate terminal
```bash
# From your server — DO NOT proceed until this works
ssh proxyuser@vps-ip 'echo "KEY AUTH OK"'
```

### Step 3: Only then harden SSH
```bash
sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
systemctl restart sshd
```

### Step 4: Verify hardened login still works
```bash
ssh proxyuser@vps-ip 'echo "STILL OK"'
```

## Common Pitfalls

| Pitfall | Why It Happens | Fix |
|---------|---------------|-----|
| `account is locked` | `useradd` without `-p` creates locked account | `usermod -p "*" username` |
| Key rejected despite correct file | Home dir owned by root (StrictModes) | `chown user:user /home/user` |
| `invalid user` in auth.log | sshd cached user list | `systemctl restart sshd` |
| `UsePAM no` breaks password auth | PAM handles password verification on Ubuntu | Keep `UsePAM yes` |
| fail2ban kills sshd | Package install triggers sshd restart | Install fail2ban **before** disabling password auth |

## Minimal Secure Setup for Proxy VPS

For a SOCKS5 proxy box, you don't need much:

```bash
# UFW: SSH only (port 22)
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp
ufw enable

# SSH: key-only auth (after verifying key works!)
PermitRootLogin no
PasswordAuthentication no

# That's it. No fail2ban needed for a proxy box.
```

## Dante SOCKS5 Proxy Setup

```bash
apt install dante-server

cat > /etc/danted.conf << 'EOF'
logoutput: syslog
internal: 127.0.0.1 port = 1080
external: eth0
socksmethod: none
clientmethod: none
client pass { from: 127.0.0.1/32 to: 0.0.0.0/0 }
socks pass { from: 127.0.0.1/32 to: 0.0.0.0/0 protocol: tcp udp }
EOF

systemctl enable --now danted
```

**Key point:** Bind to `127.0.0.1` only — the proxy is accessed via SSH tunnel, never exposed to the internet.

## SSH Tunnel (Systemd Service)

On your main server:

```ini
# /etc/systemd/system/civic-proxy-tunnel.service
[Unit]
Description=SSH tunnel to Indonesian proxy (SOCKS5)
After=network-online.target

[Service]
User=polybot
ExecStart=/usr/bin/ssh -N -L 1080:127.0.0.1:1080 \
  -o ServerAliveInterval=30 \
  -o ServerAliveCountMax=3 \
  -o ExitOnForwardFailure=yes \
  proxyuser@vps-ip
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
systemctl enable --now civic-proxy-tunnel
# Test: curl --proxy socks5h://127.0.0.1:1080 https://www.ojk.go.id
```
