# Production CI/CD Pipeline Architecture & Operations Runbook

**Application:** Smart Document Processing and Management System  
**Repository:** `https://github.com/Krish2139/Smart-Document-Management-System`  
**Deployment Platform:** AWS EC2 (`Smart-Document-Manager-Server`)  
**Elastic IP:** `44.218.34.239`  
**Operating System:** Amazon Linux 2023  
**Application Stack:** FastAPI, Python 3.12, Uvicorn, SQLite (WAL Mode), Nginx  
**AWS Integration:** Amazon S3 (`smart-doc-manager-krish-2026`), DynamoDB (`SmartDocumentManagerReplica`), AWS Lambda (`SDMDocumentMetadataProcessor`)  
**Role:** Senior DevOps Engineer & AWS Cloud Architect  

---

## Table of Contents
1. [Architecture Overview & Pipeline Lifecycle](#1-architecture-overview--pipeline-lifecycle)
2. [CI vs CD Separation & Triggers](#2-ci-vs-cd-separation--triggers)
3. [Exact Commit SHA Deployment Pattern](#3-exact-commit-sha-deployment-pattern)
4. [Critical Production Data Protection & Safe SQLite Backups](#4-critical-production-data-protection--safe-sqlite-backups)
5. [AWS Cloud Services Coexistence](#5-aws-cloud-services-coexistence)
6. [Required GitHub Secrets](#6-required-github-secrets)
7. [EC2 Server Configuration & Preparation](#7-ec2-server-configuration--preparation)
8. [SSH Network Connectivity & Security Hardening](#8-ssh-network-connectivity--security-hardening)
9. [Automated & Manual Rollback Procedures](#9-automated--manual-rollback-procedures)
10. [Pipeline Verification & Testing Drills](#10-pipeline-verification--testing-drills)
11. [Troubleshooting Guide](#11-troubleshooting-guide)

---

## 1. Architecture Overview & Pipeline Lifecycle

The deployment automation implements a decoupled, fail-safe pipeline connecting GitHub Actions to your AWS EC2 instance:

```mermaid
flowchart TD
    A["Developer pushes code to 'main'"] --> B["GitHub CI Workflow (.github/workflows/ci.yml)"]
    B --> C["Install Dependencies & Compile Python Bytecode"]
    C --> D["Execute Pytest Suite (Mocked AWS / Isolated DB)"]
    D -->|Failure| E["CI Fails & Halts (CD Never Executes)"]
    D -->|Success (All 63 Tests Pass)| F["CI Completes Successfully"]
    
    F --> G["GitHub CD Workflow (.github/workflows/cd.yml)"]
    G --> H{"Verify Trigger Guard:<br>event == 'push' && conclusion == 'success'"}
    H -->|No| I["Halt CD (E.g. PR runs never deploy)"]
    H -->|Yes| J["Extract Exact Verified Commit SHA"]
    J --> K["Open Secure SSH Connection to EC2 (44.218.34.239)"]
    K --> L["Acquire OS flock Lock (/tmp/sdm_deploy.lock)"]
    L --> M["Create Safe Timestamped SQLite Online Backup"]
    M --> N["Fetch & Checkout Exact Commit SHA"]
    N --> O["Sync Dependencies only if requirements.txt changed"]
    O --> P["Pre-Flight Compilation & FastAPI Import Verification"]
    P -->|Verification Fails| Q["Abort without restart & Roll back to previous commit"]
    P -->|Verification Passes| R["Restart sdm-app.service"]
    R --> S{"Probe http://127.0.0.1:8000/api/health (Max 15 Retries)"}
    S -->|HTTP 200 OK| T["Deployment Complete & Successful"]
    S -->|Health Check Fails| U["Auto-Rollback to previous commit & Recover Service"]
```

---

## 2. CI vs CD Separation & Triggers

| Pipeline Component | Continuous Integration (CI) | Continuous Deployment (CD) |
| :--- | :--- | :--- |
| **Workflow File** | `.github/workflows/ci.yml` | `.github/workflows/cd.yml` |
| **Trigger Events** | Pull Requests targeting `main`, direct pushes to `main`. | Successful completion of CI on `main` via `workflow_run`, or manual `workflow_dispatch`. |
| **Execution Host** | GitHub-hosted ephemeral runner (`ubuntu-latest`). | Production AWS EC2 instance (`44.218.34.239`). |
| **Target Commit** | The commit pushed or PR head commit. | **Exact commit SHA** that passed the triggering CI run. |
| **AWS Interaction** | **Zero AWS access:** Uses mocked credentials and isolated test storage. | SSH deployment to EC2; updates code without touching S3/DynamoDB/Lambda. |
| **Failure Response** | Blocks merge, sends notification. | Aborts update, rolls back code, restarts previous version, alerts team. |

### Why Pull Requests Never Deploy
In `.github/workflows/cd.yml`, the job guard condition explicitly specifies:
```yaml
if: >
  github.event_name == 'workflow_dispatch' ||
  (github.event_name == 'workflow_run' &&
   github.event.workflow_run.event == 'push' &&
   github.event.workflow_run.conclusion == 'success' &&
   github.event.workflow_run.head_branch == 'main')
```
When CI runs on a Pull Request, `github.event.workflow_run.event` is `'pull_request'`, so CD is immediately bypassed. Only when a PR is merged (firing a `push` event on `main`) and all tests pass does CD execute.

---

## 3. Exact Commit SHA Deployment Pattern

> [!CAUTION]
> **The `origin/main` Race Condition Danger:**  
> A naive deployment script that executes `git reset --hard origin/main` deploys whatever commit is currently at the tip of the remote repository. If developer Alice pushes commit `A`, triggering CI, and 30 seconds later developer Bob pushes commit `B`, when commit `A`'s CI completes, a naive CD would deploy commit `B`—which has **never been tested**!

### How Our Pipeline Eliminates This Risk:
1. When CI succeeds on commit `A`, GitHub Actions passes `workflow_run.head_sha` directly to the CD workflow.
2. The CD workflow resolves this as `TARGET_SHA`.
3. The deployment script explicitly executes:
   ```bash
   git fetch origin "$TARGET_SHA"
   git checkout "$TARGET_SHA"
   ```
4. It verifies that `git rev-parse HEAD` matches `$TARGET_SHA`.
5. Only the code that **fully passed tests** is deployed to the production server.

---

## 4. Critical Production Data Protection & Safe SQLite Backups

Production applications hold irreplaceable data. The deployment automation strictly enforces data protection:

### Strict Zero-Data-Loss Invariants:
1. **Never Runs Destructive Git Commands:** `git clean -fd`, `git clean -fdx`, and `rm -rf` are banned from deployment scripts.
2. **Untracked File Integrity:** Git checkouts only update tracked source files. Local production files (`.env`, `smart_document_manager.db`, `smart_document_manager.db-wal`, `smart_document_manager.db-shm`, and `local_storage/`) are never overwritten.
3. **Automated Point-in-Time SQLite Backup:**
   Before any code is updated, `scripts/deploy.sh` creates a timestamped online backup outside the git repository in `/home/ec2-user/backups/`:
   ```bash
   sqlite3 smart_document_manager.db ".backup '/home/ec2-user/backups/smart_document_manager_backup_$(date +%Y%m%d_%H%M%S).db'"
   ```
   *Why SQLite Online Backup API?* Standard file copies (`cp`) can corrupt SQLite databases running in Write-Ahead Logging (WAL) mode if an active transaction is writing. The `.backup` command coordinates with the SQLite lock manager to flush WAL pages safely and create a bit-perfect snapshot.
4. **Historical Backup Preservation:** Previous backup files in `/home/ec2-user/backups/` are never overwritten or deleted by deployments.

---

## 5. AWS Cloud Services Coexistence

Your production application integrates multiple AWS services:
- **Amazon S3 (`smart-doc-manager-krish-2026`):** Document object store.
- **Amazon DynamoDB (`SmartDocumentManagerReplica`):** Metadata replication table.
- **AWS Lambda (`SDMDocumentMetadataProcessor`):** Document processing triggers.
- **Amazon CloudWatch:** System and application metrics.

### Security & Access Policy:
- The EC2 instance accesses AWS services exclusively through its **EC2 IAM Instance Profile**.
- No AWS access keys (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`) are committed to Git, stored in GitHub Secrets, or hardcoded in scripts.
- The deployment process updates application code in `/home/ec2-user/Smart-Document-Management-System` without recreating or modifying any AWS IAM roles, Lambda triggers, DynamoDB tables, or S3 buckets.

---

## 6. Required GitHub Secrets

Configure these secrets in GitHub under **Settings &rarr; Secrets and variables &rarr; Actions &rarr; Repository secrets**:

| Secret Name | Required? | Example Value | Purpose |
| :--- | :---: | :--- | :--- |
| `EC2_HOST` | **Yes** | `44.218.34.239` | Public Elastic IP address of the EC2 instance. |
| `EC2_USER` | **Yes** | `ec2-user` | Operating system SSH user on Amazon Linux 2023. |
| `EC2_SSH_KEY` | **Yes** | `-----BEGIN RSA PRIVATE KEY-----...` | Private SSH key matching the key pair assigned to the EC2 instance. |
| `EC2_SSH_KNOWN_HOSTS` | **Recommended** | `44.218.34.239 ecdsa-sha2-nistp256 AAAAE2...` | Cryptographic public host key for MITM protection. |
| `EC2_PORT` | Optional | `22` | Custom SSH port (defaults to 22 if omitted). |

> [!TIP]
> To obtain the `EC2_SSH_KEY` value from your local machine, run:
> ```powershell
> Get-Content "$HOME\Downloads\smart-document-manager-key.pem" -Raw | Set-Clipboard
> ```
> And paste directly into the GitHub Secret value box.

---

## 7. EC2 Server Configuration & Preparation

Run these one-time configuration steps on your EC2 instance via SSH:

### A. Sudoers Rule for Passwordless Service Control
Allow `ec2-user` to manage `sdm-app.service` without interactive sudo password prompts:
```bash
sudo visudo -f /etc/sudoers.d/sdm-app
```
Add the line:
```text
ec2-user ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart sdm-app.service, /usr/bin/systemctl status sdm-app.service, /usr/bin/systemctl is-active sdm-app.service, /usr/bin/journalctl -u sdm-app.service*
```
Save and enforce permissions:
```bash
sudo chmod 440 /etc/sudoers.d/sdm-app
```

### B. Systemd Unit File (`/etc/systemd/system/sdm-app.service`)
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

# Security sandboxing
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```
Reload and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable sdm-app.service
sudo systemctl start sdm-app.service
```

### C. Nginx Reverse Proxy (`/etc/nginx/conf.d/sdm.conf`)
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

## 8. SSH Network Connectivity & Security Hardening

> [!WARNING]
> **Never open SSH Port 22 to `0.0.0.0/0`!**  
> Exposing port 22 to the public internet makes your EC2 instance vulnerable to brute-force credential stuffing and exploit scanners.

If GitHub Actions runners cannot reach port 22 because your EC2 Security Group restricts inbound SSH, choose one of these three industry-standard patterns:

### Option 1: GitHub Self-Hosted Runner on EC2 (Recommended)
Install a GitHub Actions self-hosted runner directly on your EC2 instance:
1. In your GitHub repository: **Settings &rarr; Actions &rarr; Runners &rarr; New self-hosted runner &rarr; Linux**.
2. Run the provided download and install commands on EC2 under `/home/ec2-user/actions-runner`.
3. Configure it as a system service: `sudo ./svc.sh install && sudo ./svc.sh start`.
4. Update `cd.yml`: Change `runs-on: ubuntu-latest` to `runs-on: self-hosted`.
- **Benefits:** **Zero open inbound ports required!** The runner connects outbound over HTTPS (port 443) to GitHub. No SSH keys needed in GitHub Secrets.

### Option 2: Dynamic Security Group Ingress Rule via AWS CLI
If using GitHub-hosted runners (`ubuntu-latest`):
1. In `cd.yml`, query the runner's public IP: `RUNNER_IP=$(curl -s https://api.ipify.org)`.
2. Add a step using an IAM role/OIDC to authorize the IP:
   ```bash
   aws ec2 authorize-security-group-ingress --group-id <SG_ID> --protocol tcp --port 22 --cidr "${RUNNER_IP}/32"
   ```
3. Run the SSH deployment.
4. Revoke the rule in an `if: always()` step:
   ```bash
   aws ec2 revoke-security-group-ingress --group-id <SG_ID> --protocol tcp --port 22 --cidr "${RUNNER_IP}/32"
   ```

### Option 3: AWS Systems Manager (SSM) Session Manager
Install `session-manager-plugin` on the runner and execute commands via `aws ssm send-command` without SSH port 22.

---

## 9. Automated & Manual Rollback Procedures

### Automated Rollback (In-Pipeline)
If the new commit fails Python compilation, fails FastAPI module import, or fails the `/api/health` HTTP probe:
1. The script displays the error and dumps recent `journalctl` logs.
2. It resets the working directory to the previously deployed commit: `git checkout "$PREV_COMMIT"`.
3. It restarts `sdm-app.service`.
4. It exits with code `1`, alerting you via GitHub Actions notifications.

### Manual Rollback Procedure
If a functional bug is discovered after a successful deployment:
```bash
# 1. SSH into the instance
ssh -i /path/to/smart-document-manager-key.pem ec2-user@44.218.34.239

# 2. Navigate to project
cd /home/ec2-user/Smart-Document-Management-System

# 3. View recent commit history
git log --oneline -n 5

# 4. Check out the previous stable commit (e.g. 7b5bf9d)
git checkout <STABLE_COMMIT_SHA>

# 5. Restart application service
sudo systemctl restart sdm-app.service

# 6. Verify health
curl -f http://127.0.0.1:8000/api/health
```

### Database Restoration from Point-in-Time Backup
If database corruption occurs, restore from the timestamped snapshot:
```bash
# 1. Stop service
sudo systemctl stop sdm-app.service

# 2. Locate latest backup
ls -lt /home/ec2-user/backups/

# 3. Restore snapshot
cp -p /home/ec2-user/backups/smart_document_manager_backup_<TIMESTAMP>.db smart_document_manager.db

# 4. Restart service
sudo systemctl restart sdm-app.service
```

---

## 10. Pipeline Verification & Testing Drills

1. **Test CI Workflow:**
   Push a branch with a test commit and open a PR to `main`. Confirm all 63 Pytest tests pass and compilation succeeds.
2. **Test CD Manual Dispatch:**
   Go to GitHub &rarr; **Actions** &rarr; select **Continuous Deployment (CD)** &rarr; click **Run workflow** on `main`. Observe live execution logs.
3. **Test Health Endpoint:**
   Verify production health from your browser or terminal:
   ```bash
   curl http://44.218.34.239/api/health
   ```
   Expected response:
   ```json
   {
     "status": "healthy",
     "app_name": "Smart Document Processing and Management System",
     "version": "1.0.0",
     "environment": "development",
     "components": {
       "database": {"status": "healthy", "details": "SQLite connected and responsive"},
       "storage": {"status": "healthy", "details": "Local storage writable and verified"}
     }
   }
   ```

---

## 11. Troubleshooting Guide

| Symptom | Root Cause | Solution |
| :--- | :--- | :--- |
| `Secret EC2_SSH_KEY is not configured` | Secret missing from GitHub repository. | Add `EC2_SSH_KEY` in GitHub Settings &rarr; Secrets &rarr; Actions. |
| `Permission denied (publickey)` | SSH key mismatch or wrong user. | Verify `EC2_USER=ec2-user` and `EC2_SSH_KEY` matches the public key in `/home/ec2-user/.ssh/authorized_keys`. |
| `Another deployment is currently executing` | Stale lockfile at `/tmp/sdm_deploy.lock`. | Check if a deployment process is running (`ps aux \| grep deploy`). If stale, remove `/tmp/sdm_deploy.lock`. |
| `sudo: a password is required` | Sudoers rule missing. | Configure `/etc/sudoers.d/sdm-app` as shown in [Section 7](#7-ec2-server-configuration--preparation). |
| `Health check probe failed (status 000)` | Service failed to start or port 8000 closed. | Inspect logs: `sudo journalctl -u sdm-app.service -n 50 --no-pager`. |
| `ssh: connect to host 44.218.34.239 port 22: Connection timed out` | EC2 Security Group blocking runner IP. | Implement Option 1 (Self-Hosted Runner) or Option 2 (Dynamic Security Group Ingress) in [Section 8](#8-ssh-network-connectivity--security-hardening). |
