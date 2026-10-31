# 🚀 Put the Help Desk on your VPS — step by step

You need: a VPS running **Ubuntu 22.04 or 24.04**, its **IP address**, and the **SSH user**
(usually `root` or `ubuntu`). Replace `YOUR_VPS_IP` and `root` below with yours.

---

## Step 1 — (Mac) Set a password for the app
Your app will be on the internet, so protect it. Open `.env` in the project folder and set:
```
APP_PASSWORD=choose-a-strong-password
SHOW_AGENT_STEPS=false
```

## Step 2 — (Mac) Copy the project to the VPS
Open **Terminal** on your Mac and run (one command):
```bash
rsync -avz --exclude '.venv' --exclude '__pycache__' --exclude '.DS_Store' \
  ~/Downloads/SE-B12/Week5/smart-helpdesk-agents/ root@YOUR_VPS_IP:~/smart-helpdesk-agents/
```
Type `yes` if asked about the fingerprint, then your VPS password.
This also copies your `.env` (with your keys) securely over SSH.

## Step 3 — (Mac) Log in to the VPS
```bash
ssh root@YOUR_VPS_IP
```

## Step 4 — (VPS) Run the setup script once
```bash
cd ~/smart-helpdesk-agents
bash deploy/setup_vps.sh
```
It takes 2–4 minutes and does everything:
1. installs Python, Nginx and tools
2. creates the virtual environment and installs the packages
3. checks your `.env`
4. runs the app as a background service — **auto-restarts if it crashes and starts again after a reboot**
5. makes it reachable from the internet (Nginx on port 80, or its own port if 80 is taken)
6. adds a firewall rule if your firewall is on (it never switches the firewall on)

At the end it prints your link → open it in any browser. 🎉
- If port 80 is free, it installs Nginx and the link is **`http://YOUR_VPS_IP`**.
- If port 80 is already used by another app (Traefik, Docker, Apache…), it leaves that app alone and
  serves the help desk on its own free port, e.g. **`http://YOUR_VPS_IP:8510`**.
You can now close Terminal — the app keeps running.

---

## Your VPS already runs Traefik (Hostinger Docker apps)? Use this for your domain
If other apps on the VPS use Traefik (ports 80/443), put the help desk on its own domain with free HTTPS:
1. In your domain's DNS, add an **A record**: Name `helpdesk` → Value `YOUR_VPS_IP`.
2. On the VPS:
   ```bash
   cd ~/smart-helpdesk-agents
   bash deploy/connect_domain_traefik.sh helpdesk.yourdomain.com
   ```
It reads your Traefik settings, runs the help desk as a Docker container with the right Traefik rules,
gets the certificate, and stops the non-Docker copy. Other apps are not touched.
Open **https://helpdesk.yourdomain.com**.

## Have a domain name and NO Traefik? (optional)
1. In your domain's DNS settings, add an **A record** pointing to `YOUR_VPS_IP`.
2. On the VPS, run the script with the domain:
   ```bash
   bash deploy/setup_vps.sh helpdesk.yourdomain.com
   ```
3. Add free HTTPS:
   ```bash
   sudo apt install -y certbot python3-certbot-nginx
   sudo certbot --nginx -d helpdesk.yourdomain.com
   ```

---

## Updating the app later
After changing code on your Mac:
```bash
# on the Mac — copy the changes (your tickets on the VPS are not touched)
rsync -avz --exclude '.venv' --exclude '__pycache__' --exclude '.DS_Store' --exclude 'logs' \
  ~/Downloads/SE-B12/Week5/smart-helpdesk-agents/ root@YOUR_VPS_IP:~/smart-helpdesk-agents/

# on the VPS — reinstall packages if needed and restart
ssh root@YOUR_VPS_IP "cd ~/smart-helpdesk-agents && bash deploy/setup_vps.sh"
```

## Everyday commands (on the VPS)
| What | Command |
|---|---|
| Is it running? | `sudo systemctl status smart-helpdesk` |
| Live logs | `sudo journalctl -u smart-helpdesk -f` (Ctrl+C to exit) |
| Restart (after editing `.env`) | `sudo systemctl restart smart-helpdesk` |
| Stop | `sudo systemctl stop smart-helpdesk` |
| Download tickets to your Mac | `scp root@YOUR_VPS_IP:~/smart-helpdesk-agents/logs/tickets.csv ~/Downloads/` |

## Troubleshooting
| Problem | Fix |
|---|---|
| Page doesn't open | Check your VPS provider's own firewall / security group allows **port 80** (and 443 for HTTPS) |
| `502 Bad Gateway` | The app is starting or crashed: `sudo journalctl -u smart-helpdesk -n 50` |
| Page loads but keeps spinning | Nginx websockets — re-run `bash deploy/setup_vps.sh` |
| "Python older than 3.10" | Use an Ubuntu 22.04 or 24.04 VPS |
| Answers fail | Check `OPENAI_API_KEY` in `~/smart-helpdesk-agents/.env`, then restart |
