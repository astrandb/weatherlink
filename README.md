[![weatherlink](https://img.shields.io/github/v/release/astrandb/weatherlink)](https://github.com/astrandb/weatherlink/releases/latest) [![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration) ![Validate with hassfest](https://github.com/astrandb/weatherlink/workflows/Validate%20with%20hassfest/badge.svg) ![Maintenance](https://img.shields.io/maintenance/yes/2023.svg) [![weatherlink_downloads](https://img.shields.io/github/downloads/astrandb/weatherlink/total)](https://github.com/astrandb/weatherlink) [![Weatherlink_downloads](https://img.shields.io/github/downloads/astrandb/weatherlink/latest/total)](https://github.com/astrandb/weatherlink)

# Weatherlink Integration for Home Assistant

This integration will represent your data on Davis Weaterlink in Home Assistant. It will query the v1 API every 5 minutes.

## Installation

Make sure you have the credentials available for your account with Weatherlink cloud. You will need the DID for your Davis weather station, your password and the API v1 access token.

### Preferred download method

- Use HACS, add this repo as a custom repository and install Weatherlink integration.
- Restart Home Assistant

### Manual download method

- Copy all files from custom_components/weatherlink in this repo to your config custom_components/weatherlink
- Restart Home Assistant

### Setup

Goto Integrations->Add and select Weatherlink - You may have to refresh browser cache to make the integration appear in the list.

Follow instructions to complete setup.

## Disclaimer

The package and its author are not affiliated with Davis Instruments or Weatherlink. Use at your own risk.

## License

The package is released under the MIT license.
