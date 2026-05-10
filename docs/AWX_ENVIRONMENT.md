# AWX Environment Summary

This document describes the AWX automation environment that has been prepared and validated for the vulnerability detection and remediation project.

## Purpose of AWX in the Project

AWX is the remediation automation platform. It does not detect vulnerabilities by itself. Its role is to execute correction actions on target machines after the backend decides that a vulnerability needs remediation.

The global remediation flow is:

```text
Wazuh detects vulnerability
Backend receives and analyzes vulnerability data
Backend maps vulnerability to a remediation policy
Backend calls the AWX API
AWX launches the correct Ansible job template
Ansible connects to the target machine
The remediation playbook applies the correction
AWX returns the job result
Backend stores and displays the remediation status
```

## AWX Server

AWX is installed on a dedicated Ubuntu virtual machine inside the lab network.

Current known values:

```text
AWX VM hostname: awx
AWX VM IP: 192.168.122.35
AWX URL: http://192.168.122.35:30080
Kubernetes distribution: k3s
Kubernetes namespace: awx
AWX instance name: awx-demo
AWX version: 24.6.1
AWX operator version: 2.19.1
```

AWX runs inside Kubernetes pods managed by the AWX Operator.

Important AWX components:

```text
awx-demo-web: provides the web dashboard and API
awx-demo-task: executes jobs and communicates with execution environments
awx-demo-postgres: stores AWX internal data
awx-operator-controller-manager: manages the AWX deployment
```

## Network

All lab machines are connected to the same libvirt virtual network:

```text
Network name: default
Subnet: 192.168.122.0/24
Bridge: virbr0
```

This network allows AWX to reach the target machines directly.

Current target IPs:

```text
debian-agent: 192.168.122.53
windows-agent: 192.168.122.82
```

These IP addresses are assigned by DHCP, so they can change after reboot. If a target becomes unreachable, the first check should be the current DHCP lease list.

From the host machine:

```bash
virsh -c qemu:///system net-dhcp-leases default
```

## Inventory

The current AWX inventory is:

```text
Inventory: Demo Inventory
```

The inventory contains the target machines that AWX can control.

Current hosts:

```text
debian-agent
windows-agent
```

## Debian Host Configuration

The Debian machine is controlled through SSH.

Host variables:

```yaml
---
ansible_host: 192.168.122.53
ansible_user: ilyass
ansible_become: true
ansible_become_method: sudo
```

Connection method:

```text
Protocol: SSH
Privilege escalation: sudo
```

Important fix applied:

```text
sudo was missing on Debian.
It was installed, and the user was added to the sudo group.
```

Validation result:

```text
AWX ad-hoc module: ping
Result: SUCCESS
Returned: "pong"
```

This confirms that AWX can connect to Debian and execute Ansible modules successfully.

## Windows Host Configuration

The Windows machine is controlled through WinRM.

Host variables:

```yaml
---
ansible_host: 192.168.122.82
ansible_connection: winrm
ansible_winrm_transport: basic
ansible_winrm_server_cert_validation: ignore
ansible_port: 5985
```

Connection method:

```text
Protocol: WinRM
Port: 5985
Transport: Basic authentication over HTTP
```

Windows configuration performed:

```powershell
Enable-PSRemoting -SkipNetworkProfileCheck -Force
winrm set winrm/config/service/auth '@{Basic="true"}'
winrm set winrm/config/service '@{AllowUnencrypted="true"}'
```

Connectivity test from AWX server:

```bash
nc -vz 192.168.122.82 5985
```

Result:

```text
Connection succeeded
```

AWX validation result:

```text
AWX ad-hoc module: win_ping
Result: SUCCESS
Returned: "pong"
```

This confirms that AWX can connect to Windows and execute Ansible Windows modules successfully.

## Credentials

AWX uses credentials to authenticate to managed hosts.

Current credential types:

```text
Debian credential: Machine credential using SSH username/password and sudo password
Windows credential: Machine credential using Windows username/password through WinRM
```

Passwords should not be stored in documentation or source code. They should remain inside AWX credentials or environment variables depending on the deployment phase.

For backend automation, credentials should not require manual input. In AWX, avoid enabling:

```text
Prompt on launch
```

for SSH password, Windows password, or privilege escalation password when the backend needs to launch jobs automatically.

## Execution Environment

An AWX Execution Environment is the container image where Ansible actually runs.

The relationship is:

```text
AWX dashboard/API -> AWX task pod -> Execution Environment -> target machine
```

For the current tests, the default AWX execution environment was enough.

Validated modules:

```text
Linux: ping
Windows: win_ping
```

Later, a custom execution environment may be created if the project needs extra Ansible collections or Python packages.

Possible future requirements:

```text
ansible.windows
community.windows
community.general
ansible.posix
pywinrm
requests
```

## What Has Been Validated

The following control paths are working:

```text
AWX -> Debian over SSH: OK
AWX -> Debian with sudo/become: OK
AWX -> Windows over WinRM: OK
AWX execution environment: OK
AWX ad-hoc command execution: OK
```

This means AWX is ready to be used as the remediation engine for the project.

## Next Step

The next step is to create real remediation playbooks.

Examples for Debian:

```text
Update package cache
Upgrade vulnerable packages
Install missing packages
Remove vulnerable packages
Restart services
Change insecure configuration files
```

Examples for Windows:

```text
Install Windows updates
Restart Windows services
Apply registry changes
Disable insecure settings
Install or remove software
```

Each remediation playbook should later become an AWX Job Template.

The backend will launch those job templates through the AWX API:

```http
POST /api/v2/job_templates/{job_template_id}/launch/
```

The backend should then monitor the job status:

```http
GET /api/v2/jobs/{job_id}/
```

## Important Security Note

The current Windows WinRM configuration is acceptable for a controlled lab because it uses Basic authentication and allows unencrypted WinRM over HTTP.

For an enterprise environment, this should be improved before production use.

Production options include:

```text
WinRM over HTTPS
Domain authentication
Kerberos authentication
Dedicated least-privilege service accounts
Firewall restrictions by source IP
Credential rotation
Secrets management
Audit logging
```

The current lab proves that the automation architecture works. The production version must harden authentication, encryption, permissions, and network access.
