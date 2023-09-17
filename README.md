[![weatherlink](https://img.shields.io/github/v/release/astrandb/weatherlink)](https://github.com/astrandb/weatherlink/releases/latest) [![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration) ![Validate with hassfest](https://github.com/astrandb/weatherlink/workflows/Validate%20with%20hassfest/badge.svg) ![Maintenance](https://img.shields.io/maintenance/yes/2023.svg) [![weatherlink_downloads](https://img.shields.io/github/downloads/astrandb/weatherlink/total)](https://github.com/astrandb/weatherlink) [![Weatherlink_downloads](https://img.shields.io/github/downloads/astrandb/weatherlink/latest/total)](https://github.com/astrandb/weatherlink)

# Weatherlink Integration for Home Assistant

This integration will represent your data from Davis Weaterlink in Home Assistant.
It will query the API every 5 minutes. The data update frequency in the API is depending on your supscription level.

## Limitations
In this first release only stations with Vue sensors are fully supported. Vantage Pro will come soon.

Current version has limited error detection and recovery and will therefore log detailed error descriptions if unforeseen thing happen.


## Installation

Make sure you have the credentials available for your account with [Weatherlink cloud service](https://www.weatherlink.com). You will need API Token and API Secret when using API V2. For the legacy API V1 you will need the DID for your Davis weather station, your password and the API v1 access token.

### Preferred download and setup method

- Use HACS
- Until this integration is included in the HACS default repository you must add this repo as a custom repository.
- Search for the integration Weatherlink and download the integration.
- Restart Home Assistant
- Go to Settings->Devices & Services->Integrations and press Add Integration. Search for Weatherlink and select it. Follow the prompts.

### Manual download and setup method

- Copy all files from custom_components/weatherlink in this repo to your config custom_components/weatherlink
- Restart Home Assistant
- Go to Settings->Devices & Services->Integrations and press Add Integration. Search for Weatherlink and select it. Follow the prompts.

## Development and contributions
The repo contains a development container that will simplify development and testing. Use VSCode and select Dev Containers: Clone Repository in Named Container Volume.

Contributions are most welcome. Optimizations, new features, translations... Please submit a PR or just leave an issue in the repo.

## Disclaimer

The package and its author are not affiliated with Davis Instruments or Weatherlink. Use at your own risk.

## License

The package is released under the MIT license.
