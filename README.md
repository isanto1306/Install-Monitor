# Install Monitor

**v0.2.65 Beta 22 – Public beta · GPL v3**

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

## Verified WebUI ports and import-path regression tests (Beta 22)

At source analysis, Install Monitor may fill in a missing published WebUI port **only when a unique container-loopback HTTP healthcheck establishes the TCP target port**. Existing mappings from manually pasted YAML remain unchanged. Image and publisher-URL imports can remap a conflicting host port only to a socket-verified free NAS port.

Database, worker, host-network and reverse-proxy-only services remain unexposed. Unknown WebUI ports are never invented. Docker-image, GitHub/URL, raw YAML and LinuxServer.io import behavior are covered by regression tests and documented in `AUDIT_IMPORT_PATHS.md`.

## Create missing Headplane config.yaml (Beta 21)

In the preview step, if the official Headplane service is missing its `/DATA/AppData/headplane/config.yaml`, the wizard asks for the **actual existing Headscale HTTP(S) URL reachable by the container** and Headplane's externally used web URL (without `/admin`). Headscale must already be running; a Tailscale client is not a Headscale server.

Only after a user action, a minimally configured `config.yaml` is created with a random 32-character cookie secret and permission mode `0600`. Existing files are never overwritten. The standard preflight is rerun, and creating this file alone does not install Headplane. Advanced OIDC/Docker integration needs separate configuration.

## Headplane and relative configuration file mounts (Beta 20)

The repository URL `https://github.com/tale/headplane` selects the publisher's Docker deployment rather than the developer-only root Compose with Caddy and a test Headscale instance. A working existing Headscale server and a real `config.yaml` are prerequisites.

For ZimaOS, safe relative file binds such as `./config.yaml:/etc/headplane/config.yaml` are resolved under the app's AppData folder. The file must **actually exist** on the NAS; Install Monitor never creates dummy files or pulls unreviewed sibling files from GitHub. File-type checks and blocking preflight remain in force.

## Named volumes on ZimaOS (Beta 19)

For **new ZimaOS installations**, ordinary Compose-managed named volumes can be mapped automatically to shared `/DATA/AppData/<app>/<volume>` bind folders. Services that share a source volume keep using the same host directory. Read-only mounts remain read-only.

Existing Docker volumes are **not** migrated or overwritten. External volumes, custom driver options and unsupported mount modes are left unchanged. If the host Docker volume list is unavailable, no automatic conversion takes place. This behavior does not apply when the target is generic Docker.

**Important:** Bind mounts do not inherit pre-populated directory contents from the image as freshly created Docker named volumes do. Some images require a manual first-run check for initialization files, data and ownership. Carefully review the final Compose preview and do not replace existing installations without backups.

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
