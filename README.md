# Install Monitor

**v0.2.61 Beta 18 – Public beta · GPL v3**

Install Monitor is a self-hosted, dark-mode application for inspecting and configuring Docker images, repositories, and Compose projects for **ZimaOS** and compatible Linux hosts. It guides users through source inspection, storage paths, ports, permissions, resource settings, and a reviewed installation process.

**[Deutsche Anleitung / German documentation](README.de.md)**


**Fresh installations start in English.** Previously selected interface languages remain unchanged after an update.
## Features

- Four app catalogs: iSanto1306 Apps, LinuxServer.io, selfh.st, and GitHub
- Docker Compose analysis and editable installation preview
- Pinned GitHub and Codeberg Docker builds; Codeberg Git LFS is downloaded under size limits before the build
- Multi-container resource, GPU, volume, and port settings
- Administrator login with username and password, with a private server-side session secret
- German, English, French, Portuguese, and Spanish UI
- Optional GitHub API integration and a local container image registry

## Important security information

**Install Monitor has access to the host Docker socket.** This gives the application extensive control over Docker and potentially the host. Keep its web interface on your private LAN/VPN, or secure access with a properly configured HTTPS reverse proxy. Do not directly expose port 9012 to the public Internet. Avoid accessing the login over unencrypted networks.

**Never commit your `.env`, `data/`, `registry/`, backups, access tokens, TOTP secrets, or host credentials to GitHub.** Only example credentials are included in the public source. No personal NAS address is embedded in the release package.

The intentionally public project identity and links (iSanto1306, PayPal, GitHub profile, Instagram) remain visible.

## Requirements

- ZimaOS or a compatible Linux host with Docker and Docker Compose v2
- Python 3.10+ for interactive credential setup
- Ports 9012/TCP (web UI) and localhost 50813/TCP (private registry) available
- Read/write access to `/DATA/AppData/Install-Monitor`
- A host Docker socket at `/var/run/docker.sock`

## Installation (new Docker Compose deployment only)

Unpack the source to a **private folder** on the NAS, then from that folder run:

```sh
sh install.sh --check
sh install.sh --docker
```

`--check` is non-destructive and requires no credentials. `--docker` refuses to overwrite existing Install Monitor containers and performs interactive setup for a username, password (12+ characters), and session secret (32+ characters or securely generated). The generated password is stored only as a salted PBKDF2-SHA256 hash in `/DATA/AppData/Install-Monitor/.env`, with restrictive file permissions. It is **not** part of the source repository.

Open `http://<YOUR-NAS-IP>:9012` **within your trusted LAN** to log in with the username and password you just configured. For remote access, use HTTPS/VPN.

This Docker deployment does **not** automatically create a native ZimaOS dashboard tile. The native ZimaOS app registration path is not implemented in this beta. A genuine first-run installation on a clean ZimaOS system and Docker image build must be validated before a production recommendation.

## Existing Install Monitor installation

This is **not** an automatic upgrade or migration package. Back up your existing configuration and data. Do not run the first-install script over an existing deployment. Update the program files deliberately and recreate containers when environment variables change; `docker restart` alone does not reload Docker Compose environment settings.

## Checks for contributors and maintainers

```sh
python3 -m unittest discover -s tests -v
python3 scripts/prepublish_check.py
python3 -m py_compile main.py setup_credentials.py
node --check static/app.js
sh -n install.sh
```

These static and simulated tests cannot replace a live Docker/ZimaOS installation test. See [Release checklist](RELEASE_CHECKLIST.md) and [privacy precheck](GITHUB_PRIVACY_PRECHECK_DE.md).

## Privacy and network access

Online catalog and image discovery calls can contact GitHub, Docker Hub, GHCR, LinuxServer.io, selfh.st, and icon/CDN providers, which may see your public IP address and queried public data. The optional GitHub token is sent to GitHub's API when relevant; if you initiate a ZimaOS installation, its credentials are transmitted to the selected host. No universal telemetry upload was identified in the reviewed source code, but a static review does not prove the absence of every possible runtime data disclosure.

## License

**Copyright © 2026 iSanto1306.** Original project source code is licensed under the **GNU General Public License v3.0 only** (`GPL-3.0-only`). Read the full [LICENSE](LICENSE). Third-party software and icon assets retain their own terms: [Third-party notices](THIRD_PARTY_NOTICES.md).

*Public beta candidate. Not yet confirmed by a clean ZimaOS real-install test.*
