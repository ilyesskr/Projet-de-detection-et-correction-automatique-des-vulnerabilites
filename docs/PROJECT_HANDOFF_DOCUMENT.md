# Enterprise Vulnerability Detection And Remediation Platform

This document explains the full project so another teammate can understand it and start working from the beginning without needing the previous conversation history.

The project is not only a lab exercise. The virtual lab is a safe reference environment for validating the concept, but the final goal is an enterprise-ready platform for real machines.

---

## 1. Project Summary

We are building a web platform that helps an enterprise:

1. Discover machines inside the enterprise environment.
2. Detect vulnerabilities on Linux and Windows endpoints.
3. Store assets and vulnerabilities in our own database.
4. Display vulnerabilities in a professional frontend dashboard.
5. Launch controlled remediation actions through Ansible/AWX.
6. Track every remediation job with approval, execution status, result, and audit logs.
7. Verify after remediation that vulnerabilities are no longer reported by Wazuh.

The platform does not replace Wazuh or AWX. It uses them.

Wazuh is responsible for security monitoring and vulnerability detection.

AWX is responsible for executing Ansible automation jobs that correct vulnerabilities.

Our backend is the brain that connects everything together.

The frontend is the enterprise interface that users interact with.

---

## 2. Main Objective

The final product should be a secure enterprise platform that gives security teams a unified workflow:

```text
Detect vulnerabilities -> Analyze risk -> Approve correction -> Execute remediation -> Verify result -> Keep audit history
```

The platform should answer questions like:

```text
Which machines are connected?
Which operating systems are used?
Which vulnerabilities exist?
Which CVEs affect which machines?
Which vulnerabilities are critical?
Which package or software caused the vulnerability?
Can we remediate it automatically?
Who approved the remediation?
Was the remediation successful?
Did Wazuh confirm that the vulnerability disappeared?
```

---

## 3. Virtual Lab Reference Environment

The project uses a virtual LAN as a reference environment for development and testing before moving to real enterprise machines.

The network is named:

```text
default
```

It uses the subnet:

```text
192.168.122.0/24
```

The bridge is usually:

```text
virbr0
```

The reference lab contains these logical machines:

| Machine | Role | OS | Purpose |
|---|---|---|---|
| `wazuh-server` | Wazuh server | Ubuntu Server | Runs Wazuh Manager, Wazuh Indexer, Wazuh Dashboard, Wazuh API |
| `debian-agent` | Vulnerable Linux endpoint | Debian | Linux machine monitored by Wazuh Agent |
| `windows-agent` | Vulnerable Windows endpoint | Windows 10 Pro | Windows machine monitored by Wazuh Agent |
| `awx-server` or AWX VM | Remediation orchestrator | Ubuntu/k3s/AWX | Runs AWX / Ansible Automation Controller |
| Host machine | Developer workstation | Kali/Linux | Runs backend, scripts, browser, libvirt tools |

Important note: IP addresses are assigned by DHCP, so they can change after reboot. Do not hardcode them permanently. Always verify them.

Useful commands:

```bash
virsh -c qemu:///system list --all
virsh -c qemu:///system net-dhcp-leases default
virsh -c qemu:///system net-info default
```

Observed lab IPs during testing included:

| Component | Observed IP |
|---|---|
| Wazuh server | `192.168.122.75` |
| Debian agent | `192.168.122.53` or `192.168.122.54` |
| Windows agent | `192.168.122.82` |
| AWX server during installation | `192.168.122.131` |

These values are examples from the lab. They must be rechecked before configuring the backend.

---

## 4. What Wazuh Does In The Project

Wazuh is the detection engine.

It has several important parts:

| Wazuh Component | Role |
|---|---|
| Wazuh Agent | Installed on each monitored machine |
| Syscollector | Collects machine inventory |
| Logcollector | Collects logs/events from the machine |
| Wazuh Manager | Receives data from agents and analyzes it |
| Vulnerability Detector | Compares collected inventory with vulnerability feeds |
| Wazuh Indexer | Stores indexed security data |
| Wazuh Dashboard | Web interface for Wazuh |
| Wazuh API | REST API used by our backend |

### 4.1 Wazuh Agent

The Wazuh Agent is installed on each endpoint.

In our lab:

```text
debian-agent has Wazuh Agent
windows-agent has Wazuh Agent
wazuh-server also appears as agent id 000
```

The agent starts automatically when the machine starts.

The user does not manually launch a vulnerability scan every time. The agent runs modules automatically based on its configuration.

### 4.2 Syscollector

Syscollector is one of the most important modules for vulnerability detection.

It collects inventory from the endpoint.

Examples of inventory:

```text
Operating system name
Operating system version
Kernel version
Installed packages
Installed software
Package versions
Network interfaces
Hardware information
Processes
Windows hotfixes / updates
```

For Linux, Syscollector can collect package data from package managers such as:

```text
apt
dpkg
rpm
yum
dnf
```

For Windows, it collects installed software and update/hotfix information from Windows sources.

### 4.3 Logcollector

Logcollector collects logs from the machine.

A log is a recorded event that happened on a system.

Examples:

```text
User login succeeded
User login failed
SSH authentication failed
Service started
Service stopped
Firewall event happened
Windows event log entry was generated
An application wrote an error message
```

Logs help Wazuh detect suspicious behavior, attacks, failed logins, malware indicators, file changes, and security events.

For vulnerability detection specifically, Syscollector inventory is more central than logs. Logs are more useful for behavior detection and incident detection.

### 4.4 Vulnerability Detector

The Wazuh Manager receives inventory from Syscollector.

Then Wazuh compares that inventory against vulnerability feeds/databases.

The general idea is:

```text
Installed package/software version + OS context -> compare with CVE database -> vulnerability result
```

Example:

```text
Machine has package openssl version X
CVE database says openssl version X is vulnerable to CVE-YYYY-ZZZZ
Wazuh reports the vulnerability for that agent
```

This is why Syscollector is critical: without accurate inventory, Wazuh cannot reliably know what vulnerabilities affect the machine.

### 4.5 Does Wazuh Scan Ports?

For vulnerability detection, Wazuh is not mainly doing port scanning.

It does not work like Nmap.

Wazuh vulnerability detection is mostly based on local inventory collected by agents:

```text
Installed packages
Installed software
OS version
Kernel version
Patch level
Hotfixes
```

Port scanning is a different technique. It detects exposed services from the network side.

Our platform can later add port scanning as an extra module, but the current Wazuh-based vulnerability flow is inventory-based.

---

## 5. What AWX Does In The Project

AWX is the remediation execution engine.

AWX is the open-source upstream project behind Ansible Automation Controller.

AWX does not work like Wazuh.

Wazuh needs agents installed on monitored machines.

AWX does not need agents on endpoints.

AWX connects remotely to machines using:

| Target OS | Connection Method |
|---|---|
| Linux | SSH |
| Windows | WinRM |

AWX executes Ansible playbooks.

A playbook is an automation file that describes what should be done on a machine.

Example actions:

```text
Update a Linux package
Install a missing security patch
Restart a service
Disable an insecure configuration
Apply a Windows update
Change a registry value
Deploy a configuration file
```

### 5.1 Why AWX Is Useful

AWX gives us:

```text
Centralized automation
Job templates
Credential management
Inventories
Execution logs
Job history
RBAC
REST API
```

Instead of manually running scripts on each machine, our backend asks AWX to run an approved job template.

### 5.2 How AWX Knows What To Fix

AWX does not automatically understand a CVE by itself.

Our backend must send context to AWX.

The backend receives vulnerability details from Wazuh, then builds `extra_vars` and sends them to an AWX job template.

Example values sent to AWX:

```json
{
  "pa_job_id": "internal-remediation-job-id",
  "asset_id": "internal-asset-id",
  "asset_hostname": "debian-agent",
  "asset_ip_address": "192.168.122.53",
  "asset_os_platform": "debian",
  "vulnerability_id": "internal-vulnerability-id",
  "cve": "CVE-YYYY-ZZZZ",
  "package_name": "openssl",
  "installed_version": "old-version",
  "fixed_version": "fixed-version",
  "remediation_action": "package_update"
}
```

Then the Ansible playbook uses these variables.

Example logic:

```text
If remediation_action == package_update:
  update package_name on the target host
```

The intelligence is split:

```text
Wazuh detects the vulnerability
Backend chooses the remediation policy
AWX executes the approved playbook
Wazuh verifies after the endpoint is rescanned
```

---

## 6. Complete Project Architecture

High-level architecture:

```text
                         +----------------------+
                         |      Frontend        |
                         |  Enterprise Web UI   |
                         +----------+-----------+
                                    |
                                    | HTTPS / REST
                                    v
                         +----------------------+
                         |       Backend        |
                         | FastAPI Orchestrator |
                         +----+-----------+-----+
                              |           |
                Wazuh API     |           | AWX API
                              |           |
                              v           v
              +--------------------+   +--------------------+
              |    Wazuh Server    |   |     AWX Server     |
              | Manager/API/Index  |   |  Ansible Jobs API  |
              +---------+----------+   +---------+----------+
                        |                        |
          Agent traffic |                        | SSH / WinRM
                        v                        v
           +----------------------+   +----------------------+
           | Enterprise Machines  |   | Enterprise Machines  |
           | Wazuh Agents         |   | Remediation Targets  |
           +----------------------+   +----------------------+

                         +----------------------+
                         |      PostgreSQL      |
                         | Assets/Vulns/Jobs    |
                         +----------------------+
```

Important rule:

```text
The frontend should communicate only with our backend.
```

The frontend should not directly call:

```text
Wazuh API
AWX API
PostgreSQL
```

This keeps credentials hidden and gives the backend full control over permissions, validation, audit logs, and business rules.

---

## 7. Full Data Flow

### 7.1 Detection Flow

```text
1. Endpoint starts.
2. Wazuh Agent starts automatically.
3. Syscollector collects inventory.
4. Logcollector collects logs/events.
5. Agent sends data to Wazuh Manager.
6. Wazuh Manager stores/analyzes data.
7. Vulnerability Detector compares inventory with vulnerability feeds.
8. Wazuh Indexer stores results.
9. Wazuh API exposes agents and vulnerabilities.
10. Backend calls Wazuh API.
11. Backend normalizes data.
12. Backend stores assets and vulnerabilities in PostgreSQL.
13. Frontend displays the results.
```

### 7.2 Remediation Flow

```text
1. User sees vulnerability in frontend.
2. User requests remediation.
3. Backend creates a remediation job with status pending_approval.
4. Supervisor/security admin approves the job.
5. Backend launches the related AWX job template.
6. Backend sends vulnerability context to AWX as extra_vars.
7. AWX runs the Ansible playbook on the target machine.
8. AWX returns job status.
9. Backend stores the AWX job id and result.
10. Backend refreshes AWX job status until completed.
11. Wazuh rescans the endpoint.
12. Backend syncs Wazuh vulnerabilities again.
13. If the vulnerability disappears, backend marks it fixed.
14. Audit logs preserve the full history.
```

---

## 8. Wazuh API Usage

The backend uses the Wazuh REST API.

### 8.1 Authentication

Wazuh API authentication is done with username/password.

The backend sends:

```http
POST /security/user/authenticate?raw=true
```

Then Wazuh returns a token.

The backend uses the token like this:

```http
Authorization: Bearer <token>
```

The backend should regenerate the token when needed.

Never hardcode Wazuh credentials in source code.

They must be stored in `.env` or in a production secret manager.

### 8.2 Important Wazuh API Endpoints

| Endpoint | Purpose |
|---|---|
| `GET /manager/info` | Check Wazuh Manager/API health |
| `GET /agents` | List Wazuh agents |
| `GET /vulnerability/{agent_id}` | List vulnerabilities for one agent |

### 8.3 Important Agent Fields

Useful fields from `/agents`:

| Field | Meaning |
|---|---|
| `id` | Wazuh agent id |
| `name` | Hostname / agent name |
| `ip` | IP address seen by Wazuh |
| `status` | `active`, `disconnected`, etc. |
| `version` | Wazuh Agent version |
| `os.name` | Operating system name |
| `os.version` | OS version |
| `os.platform` | OS platform |
| `lastKeepAlive` | Last heartbeat from the agent |

### 8.4 Important Vulnerability Fields

Useful fields from `/vulnerability/{agent_id}`:

| Field | Meaning |
|---|---|
| `cve` | CVE identifier |
| `severity` | Severity level |
| `title` | Vulnerability title |
| `package.name` | Affected package/software |
| `package.version` | Installed vulnerable version |
| `condition` | Version condition that made it vulnerable |
| `published` | CVE publication date |
| `updated` | CVE update date |
| `references` | External references |
| `score.base` | CVSS score if available |
| `status` | Vulnerability status |

Different machines can return different fields because:

```text
Linux and Windows expose different inventory data
Some vulnerabilities have more metadata than others
Some packages have fixed versions while others do not
Different Wazuh versions may shape fields slightly differently
```

The backend must therefore normalize the API response before storing it.

---

## 9. AWX API Usage

The backend uses the AWX REST API.

### 9.1 Important AWX API Endpoints

| Endpoint | Purpose |
|---|---|
| `GET /api/v2/ping/` | Check AWX API health |
| `POST /api/v2/job_templates/{id}/launch/` | Launch a remediation job template |
| `GET /api/v2/jobs/{id}/` | Check the status/result of a launched job |

### 9.2 Launching A Job Template

The backend sends:

```http
POST /api/v2/job_templates/{job_template_id}/launch/
```

With body:

```json
{
  "extra_vars": {
    "asset_hostname": "debian-agent",
    "asset_ip_address": "192.168.122.53",
    "cve": "CVE-YYYY-ZZZZ",
    "package_name": "openssl",
    "fixed_version": "example-version",
    "remediation_action": "package_update"
  }
}
```

AWX then creates a job and returns an AWX job id.

The backend stores this AWX job id in its own database.

### 9.3 AWX Job Status

Common AWX statuses:

```text
new
pending
waiting
running
successful
failed
error
canceled
```

The backend maps these to our platform statuses:

| AWX Status | Platform Status |
|---|---|
| `new`, `pending`, `waiting`, `running` | `running` |
| `successful` | `verification_pending` |
| `failed`, `error` | `failed` |
| `canceled` | `cancelled` |

After `verification_pending`, the backend should resync Wazuh vulnerabilities. If the vulnerability disappears, the platform marks it as `fixed`.

---

## 10. Backend Role

The backend is the orchestrator.

It must be developed as the central orchestrator responsible for:

```text
Calling Wazuh API
Calling AWX API
Normalizing API data
Storing data in PostgreSQL
Exposing safe endpoints to the frontend
Protecting external credentials
Managing remediation jobs
Enforcing approval workflow
Recording audit logs
Preparing extra_vars for AWX
Refreshing AWX job status
Triggering Wazuh resync after remediation
```

The backend development workspace can be organized here:

```text
/home/ilyass/Desktop/PA_development/backend
```

Main backend technologies:

| Technology | Usage |
|---|---|
| Python | Main backend language |
| FastAPI | REST API framework |
| Pydantic | Settings and schemas |
| SQLAlchemy | ORM/database layer |
| Alembic | Database migrations |
| PostgreSQL | Main database |
| Redis | Future queue/cache support |
| httpx | Async HTTP client for Wazuh/AWX |
| pytest | Automated tests |
| Docker Compose | Local PostgreSQL/Redis services |

---

## 11. Target Backend Folder Structure

The backend should be built with a clean structure similar to this:

```text
PA_development/
  .env.example
  .env
  docker-compose.yml
  README.md
  backend/
    app/
      main.py
      api/
        routes/
          health.py
          integrations.py
          sync.py
          assets.py
          vulnerabilities.py
          remediation.py
          audit.py
      core/
        config.py
        security.py
      db/
        base.py
        session.py
      models/
        asset.py
        vulnerability.py
        remediation.py
        audit.py
      schemas/
        asset.py
        vulnerability.py
        remediation.py
        audit.py
        common.py
      services/
        wazuh_client.py
        ansible_client.py
        sync_service.py
        remediation_service.py
        audit_service.py
        normalizers.py
    alembic/
      env.py
      versions/
        0001_initial_schema.py
    requirements.txt
    pyproject.toml
  tests/
    test_api_smoke.py
    test_normalizers.py
```

---

## 12. Backend Database Model

The backend should create and maintain these database tables:

```text
assets
vulnerabilities
remediation_jobs
audit_logs
alembic_version
```

### 12.1 `assets`

Stores machines discovered from Wazuh agents.

Typical fields:

```text
id
wazuh_agent_id
hostname
ip_address
status
wazuh_version
os_name
os_version
os_platform
last_keep_alive
notes
created_at
updated_at
```

### 12.2 `vulnerabilities`

Stores vulnerabilities detected by Wazuh.

Typical fields:

```text
id
asset_id
cve
severity
title
package_name
installed_version
fixed_version
published_at
updated_at
references
raw_payload
status
created_at
updated_at
```

### 12.3 `remediation_jobs`

Stores remediation requests and execution results.

Typical fields:

```text
id
asset_id
vulnerability_id
engine
action
status
created_by
approved_by
approved_at
awx_job_template_id
awx_job_id
requested_payload
result_payload
error_message
created_at
updated_at
```

### 12.4 `audit_logs`

Stores important actions.

Examples:

```text
sync.wazuh.agents
sync.wazuh.vulnerabilities
remediation.job.created
remediation.job.approved
remediation.job.launched
```

Audit logs are important for enterprise usage because every sensitive action must be traceable.

---

## 13. Backend API Endpoints

The backend base URL in development is:

```text
http://localhost:8000
```

The API prefix is:

```text
/api/v1
```

OpenAPI documentation:

```text
http://localhost:8000/docs
```

### 13.1 Public Health

```http
GET /health
```

Checks if the FastAPI process is running.

### 13.2 Protected Health

```http
GET /api/v1/health
```

Checks backend and database.

### 13.3 Integrations

```http
GET /api/v1/integrations/wazuh/health
GET /api/v1/integrations/ansible/health
```

Checks if Wazuh and AWX are reachable.

### 13.4 Sync

```http
POST /api/v1/sync/wazuh/agents
POST /api/v1/sync/wazuh/vulnerabilities
```

Pulls data from Wazuh into our database.

### 13.5 Assets

```http
GET /api/v1/assets
GET /api/v1/assets/{asset_id}
PATCH /api/v1/assets/{asset_id}
GET /api/v1/assets/{asset_id}/vulnerabilities
```

Used by the frontend to display machines.

### 13.6 Vulnerabilities

```http
GET /api/v1/vulnerabilities
```

Supports filters:

```text
asset_id
severity
status
cve
```

### 13.7 Remediation

```http
POST /api/v1/remediation/jobs
GET /api/v1/remediation/jobs
GET /api/v1/remediation/jobs/{job_id}
POST /api/v1/remediation/jobs/{job_id}/approve
POST /api/v1/remediation/jobs/{job_id}/launch
POST /api/v1/remediation/jobs/{job_id}/refresh
```

### 13.8 Audit

```http
GET /api/v1/audit-logs
```

---

## 14. Security Model

The project is intended for enterprise use, so security is not optional.

### 14.1 Secrets

Never commit these files:

```text
.env
token.txt
private SSH keys
AWX admin password files
database passwords
Wazuh passwords
```

Development secrets are stored in:

```text
/home/ilyass/Desktop/PA_development/.env
```

Production should use a real secret manager, for example:

```text
HashiCorp Vault
Kubernetes Secrets
Cloud secret manager
Enterprise password vault
```

### 14.2 Backend API Key

The backend supports an API key.

If `APP_API_KEY` is configured, protected endpoints require:

```http
X-API-Key: <configured-api-key>
```

This is simple development protection.

For production, we should add:

```text
User authentication
RBAC
HTTPS
JWT/OAuth2 or enterprise SSO
Audit logs for every action
Rate limiting
IP allowlists where appropriate
```

### 14.3 Frontend Security Rule

The frontend must never store or expose:

```text
Wazuh credentials
AWX credentials
Database credentials
SSH keys
WinRM credentials
```

The frontend talks only to our backend.

### 14.4 Remediation Safety

Automatic correction is risky in enterprise systems.

Therefore the workflow should include:

```text
Create remediation request
Validate request
Require approval
Launch AWX job
Track execution
Verify after Wazuh resync
Keep audit trail
```

Some low-risk fixes can later be auto-approved by policy, but the default enterprise workflow should be controlled and auditable.

---

## 15. Development Setup From The Beginning

### 15.1 Start PostgreSQL And Redis

From:

```bash
cd /home/ilyass/Desktop/PA_development
```

Start services:

```bash
docker-compose up -d postgres redis
```

Check:

```bash
docker-compose ps
```

### 15.2 Create Environment File

Use:

```bash
cp .env.example .env
```

Then configure:

```env
DATABASE_URL=postgresql+psycopg://pa_user:pa_password@localhost:5432/pa_db
WAZUH_API_URL=https://<wazuh-server-ip>:55000
WAZUH_API_USER=<wazuh-api-user>
WAZUH_API_PASSWORD=<wazuh-api-password>
WAZUH_VERIFY_TLS=false
AWX_API_URL=http://<awx-server-ip>:30080
AWX_API_USER=<awx-user>
AWX_API_PASSWORD=<awx-password>
AWX_VERIFY_TLS=false
APP_API_KEY=<local-backend-api-key>
```

Do not share the real `.env` file.

### 15.3 Install Backend Dependencies

```bash
cd /home/ilyass/Desktop/PA_development/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 15.4 Run Database Migrations

```bash
cd /home/ilyass/Desktop/PA_development/backend
source .venv/bin/activate
alembic upgrade head
```

### 15.5 Run Backend

```bash
cd /home/ilyass/Desktop/PA_development/backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 15.6 Test Backend

```bash
curl http://localhost:8000/health
```

Protected endpoint example:

```bash
curl -H "X-API-Key: <APP_API_KEY>" \
  http://localhost:8000/api/v1/health
```

Wazuh health:

```bash
curl -H "X-API-Key: <APP_API_KEY>" \
  http://localhost:8000/api/v1/integrations/wazuh/health
```

AWX health:

```bash
curl -H "X-API-Key: <APP_API_KEY>" \
  http://localhost:8000/api/v1/integrations/ansible/health
```

Sync Wazuh agents:

```bash
curl -X POST -H "X-API-Key: <APP_API_KEY>" \
  http://localhost:8000/api/v1/sync/wazuh/agents
```

Sync vulnerabilities:

```bash
curl -X POST -H "X-API-Key: <APP_API_KEY>" \
  http://localhost:8000/api/v1/sync/wazuh/vulnerabilities
```

List assets:

```bash
curl -H "X-API-Key: <APP_API_KEY>" \
  http://localhost:8000/api/v1/assets
```

List vulnerabilities:

```bash
curl -H "X-API-Key: <APP_API_KEY>" \
  http://localhost:8000/api/v1/vulnerabilities
```

### 15.7 Run Tests

```bash
cd /home/ilyass/Desktop/PA_development/backend
source .venv/bin/activate
pytest
```

---

## 16. Frontend Responsibilities

The frontend teammate should build an enterprise-grade UI that consumes only the backend API.

Main pages:

```text
Dashboard
Assets
Asset details
Vulnerabilities
Vulnerability details
Remediation jobs
Approval queue
Audit logs
Integration status
Settings
```

### 16.1 Dashboard Should Show

```text
Total assets
Active agents
Disconnected agents
Open vulnerabilities
Critical vulnerabilities
High vulnerabilities
Remediation jobs pending approval
Remediation jobs running
Remediation jobs failed
Remediation jobs verification pending
```

### 16.2 Assets Page

Should show:

```text
Hostname
IP address
OS
Agent status
Wazuh agent version
Last keep alive
Number of open vulnerabilities
Highest severity
```

### 16.3 Vulnerabilities Page

Should show:

```text
CVE
Severity
Affected asset
Affected package/software
Installed version
Fixed version
Status
Published date
Remediation action button
```

Filters:

```text
Severity
Status
Asset
CVE
Package
OS
```

### 16.4 Remediation Page

Should show:

```text
Job id
Asset
Vulnerability
Action
Status
Created by
Approved by
AWX job id
Created time
Updated time
Result/error
```

Actions:

```text
Create remediation request
Approve remediation
Launch remediation
Refresh AWX status
Resync vulnerabilities after remediation
```

The UI should make dangerous actions explicit and visible. For example, launching a remediation should require confirmation.

---

## 17. Remediation Policy

The backend must support launching approved AWX job templates.

An important backend responsibility is to build a remediation policy layer.

This layer decides:

```text
Which vulnerability can be corrected automatically?
Which AWX job template should be used?
Which parameters should be passed?
Does the job require approval?
Is the target Linux or Windows?
Is the fix safe?
Does it require reboot?
Does it require maintenance window?
```

Example policy idea:

| Condition | Action |
|---|---|
| Linux package vulnerability with fixed version | Run package update playbook |
| Windows missing security update | Run Windows update playbook |
| Config issue | Run hardening playbook |
| Critical server | Require approval |
| Unknown CVE/package | Manual review |

The policy should never blindly execute arbitrary commands from API input.

The safe model is:

```text
User selects vulnerability
Backend validates asset and vulnerability
Backend matches a known policy
Backend creates pending job
Admin approves
Backend launches a predefined AWX template
```

---

## 18. AWX Setup Concepts

Inside AWX we need:

```text
Organization
Inventory
Hosts
Credentials
Project
Job Templates
```

### 18.1 Inventory

AWX inventory contains target machines.

Example:

```text
debian-agent
windows-agent
```

### 18.2 Credentials

Linux credentials:

```text
SSH username
SSH private key or password
Privilege escalation method
```

Windows credentials:

```text
WinRM username
WinRM password
Connection settings
```

### 18.3 Project

AWX project points to the repository containing Ansible playbooks.

Example playbooks:

```text
linux_package_update.yml
windows_update.yml
restart_service.yml
verify_package_version.yml
```

### 18.4 Job Templates

Job templates define which playbook to run.

Example templates:

```text
Linux Package Update
Windows Security Update
Linux Service Restart
Windows Service Restart
```

The backend launches job templates through the AWX API.

---

## 19. Virtual LAN Rebuild Guide

If the teammate needs to rebuild the lab:

### 19.1 Confirm libvirt default network

```bash
virsh -c qemu:///system net-list --all
virsh -c qemu:///system net-info default
```

If inactive:

```bash
virsh -c qemu:///system net-start default
virsh -c qemu:///system net-autostart default
```

### 19.2 Wazuh Server

Install Ubuntu Server in a VM.

Recommended hostname:

```text
wazuh-server
```

Connect VM network adapter to:

```text
default
```

Install Wazuh all-in-one server.

Wazuh components:

```text
Wazuh Manager
Wazuh Indexer
Wazuh Dashboard
Filebeat
Wazuh API
```

After installation, access:

```text
https://<wazuh-server-ip>
```

Wazuh API:

```text
https://<wazuh-server-ip>:55000
```

### 19.3 Debian Agent

Install Debian in a VM.

Recommended hostname:

```text
debian-agent
```

Install Wazuh Agent and configure it to point to the Wazuh Manager IP.

Check from Wazuh Dashboard that the Debian agent appears as active.

### 19.4 Windows Agent

Install Windows 10/11 Pro in a VM.

Install Wazuh Agent for Windows.

Configure the manager IP as the Wazuh server IP.

Check from Wazuh Dashboard that the Windows agent appears as active.

### 19.5 AWX Server

AWX can be installed in a separate VM on the same `default` network.

AWX can be deployed with this approach:

```text
Ubuntu cloud VM
k3s Kubernetes
AWX Operator
AWX custom resource
NodePort service on port 30080
```

Expected AWX URL:

```text
http://<awx-server-ip>:30080
```

Always verify the current AWX IP:

```bash
virsh -c qemu:///system net-dhcp-leases default
```

---

## 20. Backend Implementation Roadmap

The backend should be built from the beginning following this order:

```text
1. Initialize the backend project structure.
2. Configure FastAPI.
3. Configure environment variables through .env.
4. Configure PostgreSQL connection.
5. Configure Alembic migrations.
6. Create SQLAlchemy models.
7. Create Pydantic schemas.
8. Implement Wazuh API client.
9. Implement AWX API client.
10. Implement normalization logic for Wazuh responses.
11. Implement asset sync from Wazuh agents.
12. Implement vulnerability sync from Wazuh vulnerability endpoints.
13. Implement asset and vulnerability listing endpoints.
14. Implement remediation job creation.
15. Implement approval workflow.
16. Implement AWX job launch.
17. Implement AWX job status refresh.
18. Implement post-remediation Wazuh verification.
19. Implement audit logging.
20. Add automated tests.
21. Add production security hardening.
22. Prepare deployment documentation.
```

The backend should expose a stable API that the frontend can consume. The frontend teammate should not depend directly on Wazuh or AWX internals.

The implementation must still include these planned components:

```text
PostgreSQL database
Redis for future background jobs/cache
FastAPI REST API
Wazuh API client
AWX API client
Database migrations
Asset synchronization
Vulnerability synchronization
Remediation job lifecycle
Approval workflow
Audit logs
Tests
Production security configuration
```

---

## 21. What The Teammate Should Do Next

If working on backend:

```text
1. Start PostgreSQL and Redis.
2. Configure .env.
3. Run migrations.
4. Start FastAPI.
5. Test Wazuh health endpoint.
6. Sync agents.
7. Sync vulnerabilities.
8. Verify database records.
9. Configure AWX.
10. Test AWX health endpoint.
11. Create test remediation job.
12. Approve job.
13. Launch job.
14. Refresh job status.
15. Resync vulnerabilities after remediation.
```

If working on frontend:

```text
1. Use backend OpenAPI docs at /docs.
2. Do not call Wazuh or AWX directly.
3. Build pages around backend endpoints.
4. Include API key header if APP_API_KEY is enabled.
5. Display loading/error states clearly.
6. Add confirmation before remediation launch.
7. Add professional dashboard visualizations.
8. Add audit log view.
```

If working on AWX/Ansible:

```text
1. Make sure AWX is reachable.
2. Create AWX organization.
3. Create inventories for Linux and Windows machines.
4. Create credentials for SSH and WinRM.
5. Create project linked to Ansible playbook repository.
6. Create job templates.
7. Test playbooks manually in AWX.
8. Connect job template ids to backend remediation jobs.
```

---

## 22. Acceptance Criteria

The project is working when:

```text
Wazuh shows active Linux and Windows agents
Backend can authenticate to Wazuh API
Backend can sync agents into PostgreSQL
Backend can sync vulnerabilities into PostgreSQL
Frontend displays assets and vulnerabilities from backend
User can create a remediation job
User/admin can approve a remediation job
Backend can launch an AWX job template
AWX executes playbook on the target machine
Backend can refresh AWX job status
Wazuh rescans the machine
Backend marks vulnerability fixed when it disappears from Wazuh
Audit logs show the full chain of actions
Secrets are not exposed in frontend or source code
```

---

## 23. Production Considerations

For real enterprise deployment, the `.env` file will change, but that is not the only thing.

Other production changes:

```text
Real Wazuh server URL
Real AWX/Automation Controller URL
Real database URL
Real Redis URL
Production TLS certificates
Production authentication provider
Production RBAC roles
Production logging
Production secret manager
Production backup strategy
Production network firewall rules
Production monitoring
Production deployment method
Production Ansible inventories
Production SSH/WinRM credentials
Approved remediation policies
Maintenance windows
Rollback strategy
```

Enterprise deployment must be planned carefully because remediation can change real machines.

---

## 24. Important Safety Notes

Do not expose:

```text
Wazuh API password
AWX admin password
Backend API key
Database password
SSH private keys
WinRM credentials
Temporary tokens
```

Do not run remediation automatically on production machines without:

```text
Approval
Policy validation
Testing
Rollback plan
Audit logging
Maintenance window if needed
```

Do not trust frontend input blindly.

The backend must validate:

```text
The asset exists
The vulnerability exists on that asset
The action is allowed
The job template is approved
The user has permission
The remediation payload is safe
```

---

## 25. Short Explanation For A Supervisor

The project is an enterprise vulnerability management platform.

Wazuh agents installed on enterprise machines collect system inventory and logs. Wazuh Manager analyzes that data and detects vulnerabilities by comparing installed software and OS information with vulnerability databases. Our backend uses the Wazuh API to extract assets and vulnerabilities, then stores normalized results in PostgreSQL.

For correction, Wazuh does not provide full automatic remediation. Therefore, the platform uses AWX/Ansible. The backend creates controlled remediation jobs, requires approval, then launches predefined AWX job templates through the AWX API. AWX executes Ansible playbooks on Linux machines through SSH and Windows machines through WinRM. After remediation, the platform resynchronizes Wazuh results to verify whether the vulnerability was actually corrected.

This creates a complete workflow:

```text
Detection -> Centralization -> Decision -> Approval -> Automated Correction -> Verification -> Audit
```

---

## 26. Minimal Mental Model

If the teammate remembers only one thing, remember this:

```text
Wazuh detects.
Backend decides and records.
Frontend displays and controls.
AWX remediates.
Wazuh verifies.
PostgreSQL keeps history.
```
