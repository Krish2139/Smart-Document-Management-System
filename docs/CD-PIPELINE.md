# Continuous Deployment (CD) Pipeline Documentation

**Application:** Smart Document Processing and Management System  
**Repository:** `https://github.com/Krish2139/Smart-Document-Management-System`  
**Target Environment:** AWS EC2 (`Smart-Document-Manager-Server`)  
**Host / Elastic IP:** `44.218.34.239`  
**Operating System:** Amazon Linux 2023  
**Service:** `sdm-app.service` (Systemd) | Reverse Proxy: Nginx  
**Author:** Senior DevOps Engineering  

---

## Table of Contents
1. [Overview: CI vs CD](#1-overview-ci-vs-cd)
2. [Workflow Architecture & Triggering](#2-workflow-architecture--triggering)
3. [Required GitHub Secrets](#3-required-github-secrets)
4. [EC2 Server Preparation & Systemd Setup](#4-ec2-server-preparation--systemd-setup)
5. [SSH Configuration & Host Key Verification](#5-ssh-configuration--host-key-verification)
6. [Deployment Lifecycle & Safety Guarantees](#6-deployment-lifecycle--safety-guarantees)
7. [Rollback Procedures](#7-rollback-procedures)
8. [Testing & Verification](#8-testing--verification)
9. [Troubleshooting Common Issues](#9-troubleshooting-common-issues)
10. [Security Considerations & Hardening](#10-security-considerations--hardening)

---

## 1. Overview: CI vs CD

| Metric / Phase | Continuous Integration (CI) | Continuous Deployment (CD) |
| :--- | :--- | :--- |
| **Workflow File** | `.github/workflows/ci.yml` | `.github/workflows/cd.yml` |
| **Purpose** | Validate code quality, syntax, build integrity, and test coverage. | Safely deploy validated code to the AWS EC2 production server. |
| **Trigger** | Pull Requests to `main` and direct pushes to `main`. | Successful completion of CI on the `main` branch (or manual dispatch). |
| **Environment** | Ephemeral GitHub-hosted Ubuntu runner (`ubuntu-latest`). | Production AWS EC2 instance (`Smart-Document-Manager-Server`). |
| **Artifacts** | Test reports (pytest, coverage, compilation logs). | Running systemd service (`sdm-app.service`), updated code checkout. |
| **Failure Impact** | Blocks PR merge; alerts developer without affecting production. | Aborts update, rolls back to previous commit, alerts operations. |

---

## 2. Workflow Architecture & Triggering

The CD pipeline uses GitHub Actions' native `workflow_run` event to link deployment directly to successful test runs on the `main` branch.

```mermaid
flowchart TD
    A["Developer commits & pushes to 'main'"] --> B["GitHub Action: CI Workflow (.github/workflows/ci.yml)"]
    B --> C{"Run Pytest & Dependency Builds"}
    C -->|Failure| D["CI Fails & Notifications Sent<br>(Deployment Never Triggered)"]
    C -->|Success| E["CI Completes Successfully on 'main'"]
    E --> F["GitHub Action: CD Workflow (.github/workflows/cd.yml)"]
    F --> G{"Workflow Guard Verification:<br>event == 'push' && conclusion == 'success'"}
    G -->|No| H["Halt Execution (No Action)"]
    G -->|Yes| I["Acquire Deployment Lock & Connect via SSH"]
    I --> J["Fetch Code, Verify Dependencies & Bytecode"]
    J --> K["Restart sdm-app.service & Probe /api/health"]
    K -->|Health Check 200 OK| L["Deployment Marked Successful"]
    K -->|Health Check Fails| M["Automatic Rollback to Previous Commit & Service Recovery"]
```

### Trigger Configuration
In `.github/workflows/cd.yml`:
```yaml
on:
  workflow_run:
    workflows: ["Smart Document Management System CI"]
    types:
      - completed
    branches:
      - main
  workflow_dispatch:
    inputs:
      reason:
        description: "Reason for manual deployment trigger"
        required: false
        default: "Manual deployment trigger"
```

### Job Guard Condition
```yaml
if: >
  github.event_name == 'workflow_dispatch' ||
  (github.event_name == 'workflow_run' &&
   github.event.workflow_run.event == 'push' &&
   github.event.workflow_run.conclusion == 'success')
```
- **Pull Request Protection:** When CI runs on a Pull Request targeting `main`, `event` is `'pull_request'`, so CD does **not** trigger.
- **Merge/Push Execution:** Only when the PR is merged into `main` (or code is pushed directly to `main`) and all 63 automated tests pass, CD proceeds.
- **Manual Control:** Developers can trigger deployment manually from the GitHub Actions tab via `workflow_dispatch`.

---

## 3. Required GitHub Secrets

Configure the following secrets in the GitHub repository under **Settings &rarr; Secrets and variables &rarr; Actions &rarr; Repository secrets**:

| Secret Name | Required? | Example Value | Description |
| :--- | :---: | :--- | :--- |
| `EC2_HOST` | **Yes** | `44.218.34.239` | Public Elastic IP address or DNS of the EC2 instance. |
| `EC2_USER` | **Yes** | `ec2-user` | The SSH operating system user on Amazon Linux 2023. |
| `EC2_SSH_KEY` | **Yes** | `-----BEGIN RSA PRIVATE KEY-----...` | Private SSH key (PEM / OpenSSH format) matching the EC2 key pair. |
| `EC2_SSH_KNOWN_HOSTS`| **Recommended** | `44.218.34.239 ecdsa-sha2-nistp256 AAAAE2...` | Public host key fingerprint for strict host verification. |
| `EC2_PORT` | Optional | `22` | SSH port (defaults to 22 if omitted). |

> [!IMPORTANT]
> **Host Key Security:** If `EC2_SSH_KNOWN_HOSTS` is provided, the runner performs cryptographic host verification against Man-in-the-Middle (MITM) attacks. If omitted, the workflow will use `ssh-keyscan` as a fallback.

---

## 4. EC2 Server Preparation & Systemd Setup

To ensure the deployment runner can restart the application without interactive password prompts, perform the following one-time configuration on the EC2 instance.

### Step 1: Systemd Service Unit (`/etc/systemd/system/sdm-app.service`)
Create or verify the service file:
```ini
[Unit]
Description=Smart Document Processing and Management System (FastAPI)
After=network.target

[Service]
User=ec2-user
Group=ec2-user
WorkingDirectory=/home/ec2-user/Smart-Document-Management-System
EnvironmentFile=/home/ec2-user/Smart-Document-Management-System/.env
ExecStart=/home/ec2-user/Smart-Document-Management-System/venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=always
RestartSec=5
KillMode=mixed
TimeoutStopSec=15

# Sandboxing & Security
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable sdm-app.service
sudo systemctl start sdm-app.service
```

### Step 2: Sudoers Configuration for `ec2-user` (`/etc/sudoers.d/sdm-app`)
Grant `ec2-user` scoped permission to manage `sdm-app.service` without requiring a password:
```bash
sudo visudo -f /etc/sudoers.d/sdm-app
```
Add the following line:
```
ec2-user ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart sdm-app.service, /usr/bin/systemctl status sdm-app.service, /usr/bin/systemctl is-active sdm-app.service, /usr/bin/journalctl -u sdm-app.service*
```
Save and ensure file permissions:
```bash
sudo chmod 440 /etc/sudoers.d/sdm-app
```

### Step 3: Nginx Reverse Proxy (`/etc/nginx/conf.d/sdm.conf`)
Ensure Nginx routes external HTTP/HTTPS traffic to the Uvicorn application on port 8000:
```nginx
server {
    listen 80;
    server_name 44.218.34.239;

    client_max_body_size 30M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 90;
    }
}
```
Reload Nginx:
```bash
sudo nginx -t && sudo systemctl reload nginx
```

---

## 5. SSH Configuration & Host Key Verification

### Obtaining the Host Key for `EC2_SSH_KNOWN_HOSTS`
Run this command from your local terminal to obtain the cryptographic host key:
```bash
ssh-keyscan -H 44.218.34.239
```
Copy the output line (e.g. `44.218.34.239 ssh-ed25519 AAAAC3...`) and save it as the repository secret `EC2_SSH_KNOWN_HOSTS`.

### Verifying SSH Access Locally
Verify connection using your private key:
```bash
ssh -i /path/to/ec2-key.pem ec2-user@44.218.34.239 "uptime"
```

---

## 6. Deployment Lifecycle & Safety Guarantees

Every deployment follows a strict 7-stage pipeline executing directly on the target instance:

```
[1/7] Acquire Lock  --> [2/7] Pre-flight Check --> [3/7] Git Controlled Fetch
        |
[4/7] Dependency Sync -> [5/7] Bytecode Validation -> [6/7] Service Restart
        |
[7/7] Health Verification (Probe /api/health with automatic rollback)
```

### Critical Production Protections:
1. **Never Overwrites `.env`:** The deployment script checks for the existence of `.env` before and after updating code. Because `.env` is listed in `.gitignore`, Git does not track or overwrite it.
2. **Never Deletes Production Storage:** `local_storage/documents/` and `local_storage/temp/` are untouched.
3. **Preserves SQLite Database:** `smart_document_manager.db` (including `-wal` and `-shm` write-ahead logs) is untracked and retained in place across all deployments.
4. **Preserves AWS Cloud Integrations:** DynamoDB replication, Lambda triggers, S3 storage providers, and CloudWatch metrics configs are preserved.
5. **No Blind `git clean`:** We deliberately omit `git clean -fdx`.
6. **Concurrent Deployment Lock:** Uses `flock -n /tmp/sdm_deploy.lock` and GitHub Actions `concurrency` to prevent simultaneous overlapping deployments.
7. **Zero-Downtime Validation:** Python bytecode (`compileall`) and FastAPI module loading are checked *before* restarting the systemd service. If syntax or dependencies are broken, the service is never restarted.

---

## 7. Rollback Procedures

### Automatic Rollback (Built into the Pipeline)
If the new code fails Python bytecode compilation, fails module import, or if the systemd health probe fails to return `HTTP 200` from `/api/health` within 30 seconds:
1. The deployment script catches the failure immediately.
2. It prints the latest journalctl logs: `sudo journalctl -u sdm-app.service -n 50 --no-pager`.
3. It automatically rolls back Git to the previous commit: `git reset --hard $PREV_COMMIT`.
4. It restarts `sdm-app.service` using the previous stable code.
5. It fails the GitHub Actions job with exit code `1` to alert the team.

### Manual Rollback (Operator Emergency Run)
If an unexpected behavioral bug appears in production after a successful deployment, roll back manually via SSH:

```bash
# 1. Connect to EC2
ssh -i /path/to/key.pem ec2-user@44.218.34.239

# 2. Navigate to project
cd /home/ec2-user/Smart-Document-Management-System

# 3. View deployment history
git log --oneline -n 5

# 4. Roll back to the previous stable commit (e.g., abc1234)
git reset --hard <STABLE_COMMIT_HASH>

# 5. Restart the service
sudo systemctl restart sdm-app.service

# 6. Verify health
curl -f http://127.0.0.1:8000/api/health
```

---

## 8. Testing & Verification

### Dry-Run / Manual Trigger
1. In the GitHub repository, navigate to the **Actions** tab.
2. Select **Continuous Deployment (CD)** from the left sidebar.
3. Click **Run workflow** &rarr; select branch `main` &rarr; click **Run workflow**.
4. Observe real-time deployment logs for each stage:
   - Acquiring deployment lock
   - Verifying `.env`
   - Git fetch & checkout
   - Dependency checksum evaluation
   - Bytecode compilation check
   - Service restart & HTTP health check

### Automated Production Flow
1. Create a feature branch and submit a Pull Request to `main`.
2. Verify that **CI (Smart Document Management System CI)** executes tests and passes. (Notice that CD is **not** triggered yet).
3. Merge the Pull Request into `main`.
4. The CI workflow triggers automatically on push to `main`.
5. Upon CI success, the **Continuous Deployment (CD)** workflow starts automatically and deploys the code to EC2.

---

## 9. Troubleshooting Common Issues

| Issue / Error | Probable Cause | Resolution |
| :--- | :--- | :--- |
| `Secret EC2_SSH_KEY is not configured` | Missing repository secrets in GitHub. | Add `EC2_SSH_KEY`, `EC2_HOST`, and `EC2_USER` in Repository Settings &rarr; Secrets. |
| `Permission denied (publickey)` | SSH key mismatch or wrong user. | Verify `EC2_USER` is `ec2-user` and `EC2_SSH_KEY` matches the public key in `~/.ssh/authorized_keys`. |
| `Another deployment is currently in progress` | Stale lockfile at `/tmp/sdm_deploy.lock`. | Check if a deployment is running (`ps aux \| grep deploy`). If stale, remove `/tmp/sdm_deploy.lock`. |
| `sudo: a password is required` | Missing sudoers rule for `systemctl`. | Add the `/etc/sudoers.d/sdm-app` entry detailed in [Section 4](#4-ec2-server-preparation--systemd-setup). |
| `Health check probe failed (000 / 500)` | App startup crash or database issue. | Review application logs: `sudo journalctl -u sdm-app.service -n 100 --no-pager`. |
| `requirements.txt install timeout` | Slow pip compilation on small EC2 instance. | Ensure pre-built wheels are used: `pip install --no-cache-dir -r requirements.txt`. |

---

## 10. Security Considerations & Hardening

1. **Least Privilege SSH Access:**
   - Restrict inbound SSH port 22 in the EC2 Security Group to GitHub Actions CIDR blocks or your bastion/VPN IP rather than `0.0.0.0/0`.
   - Consider AWS Systems Manager (SSM) Session Manager for agent-based SSH without exposing port 22.
2. **Key Hygiene:**
   - Use an ED25519 or 4096-bit RSA SSH deployment key dedicated solely to CD automation.
   - Rotate deployment keys periodically.
3. **Strict File Permissions on EC2:**
   - `.env`: `chmod 600 .env` (readable only by `ec2-user`).
   - SQLite DB: `chmod 600 smart_document_manager.db*`.
   - `local_storage/`: `chmod 700 local_storage/documents`.
4. **Environment Secrets Management:**
   - Sensitive AWS credentials (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`) should remain in `.env` on EC2 or be delivered securely via EC2 IAM Roles (`Instance Profile`) rather than passing through GitHub Secrets.
