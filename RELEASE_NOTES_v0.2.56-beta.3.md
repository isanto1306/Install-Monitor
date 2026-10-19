# Install Monitor v0.2.56-beta.3

Third public beta — ZimaOS target address and reverse proxy installation fix.

## Fixed
- The installation wizard no longer inserts the Install Monitor browser domain into the ZimaOS address field. It preselects a hostname only when the browser is already on a LAN/loopback/Tailscale address.
- A clear five-language explanation identifies the **ZimaOS administration address** instead of the Install Monitor public hostname.
- Reverse-proxy installations have an **optional internal ZimaOS address** field. The entered LAN address is used for the ZimaOS API, without requiring `IM_INTERNAL_ZIMAOS_URL` in Docker environment variables.
- Existing `IM_INTERNAL_ZIMAOS_URL` configurations continue working when the new field is left empty.
- Installation verification uses the same private internal target as installation.
- Invalid or missing private targets are rejected before installation, with an actionable explanation. Public proxy destinations cannot be substituted for the internal ZimaOS API.
- No changes to the working authenticator host-removal behavior or the original icon.

## Scope and security
- Both administrator credentials and the optional internal ZimaOS address are used only for the current installation request; no values are persisted as browser settings.
- A public, allowlisted ZimaOS reverse proxy still requires a valid one-time authenticator code for installation.
- Private destinations remain subject to the existing LAN/Tailscale address validation.
- No existing Compose application is overwritten by Install Monitor.

## Test guidance
1. Open the installation wizard, then enter the local ZimaOS address (e.g. `http://192.168.1.50`) and the normal ZimaOS administrator credentials.
2. Optionally enter an approved HTTPS ZimaOS proxy domain in the main field and the ZimaOS LAN address in the new internal-address field. Provide an authenticator code.
3. Confirm installation progress and verify the target application's Docker containers started successfully.

**Beta software:** GitHub CI validates syntax and isolated routing. A real NAS installation still requires the administrator's credentials and confirmation.
