# Install Monitor v0.2.56-beta.2

**Second public beta release — English by default on first launch.**

## Changes
- English is now the default interface language when Install Monitor is opened in a browser with no previously saved preference.
- The first-load HTML language and settings language indicator now start in English.
- Existing language choices stored in the browser remain unchanged during upgrades.
- All five supported UI languages remain available: English, German, French, Portuguese and Spanish.
- Backend version, local Compose installer, tests and GHCR Beta 2 image metadata have been synchronized.
- The existing Install Monitor icon and the four separate app catalogs are unchanged.

## Installation and testing
- New ZimaOS App Store installs require a unique administrator username, a password of at least 12 characters and a random session secret of at least 32 characters.
- Do not install over an existing Install Monitor container or reuse its ports without backing up and stopping it first.
- This remains beta software; a clean real-world ZimaOS installation must still be verified.
- Docker socket access provides broad Docker/host privileges. Keep the UI on a trusted LAN/VPN or behind a secured HTTPS reverse proxy.

License: GNU GPL v3.0 only.
