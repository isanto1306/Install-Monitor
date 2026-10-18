# Install Monitor v0.2.56-beta.1

**First public source beta candidate.**

### Included

- Four independent app catalogs (iSanto1306, LinuxServer.io, selfh.st, GitHub)
- Compose analysis and guided multi-container setup, including CPU/RAM/GPU options
- Five UI languages: DE, EN, FR, PT, ES
- Username/password authentication, secure first-install credential generator and private server secret
- Local Docker Compose installation flow and localhost-bound image registry
- Full GNU GPL v3.0-only license and third-party notices

### Known limitations

- No verified clean-install test against a physical ZimaOS NAS in the release environment
- No automatic native ZimaOS dashboard-tile registration
- A Docker socket grants broad permissions; restrict access to LAN/VPN or HTTPS reverse proxy
- Not an in-place migration tool for existing Install Monitor deployments

### Verification

Six offline installer tests, Python/JavaScript syntax checks, Compose source checks and secret-pattern scans. A full Docker daemon integration test is still required.

**Do not publish the original NAS backup or credential files. Publish only the sanitized release source.**
