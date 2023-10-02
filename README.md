[![weatherlink](https://img.shields.io/github/v/release/astrandb/weatherlink)](https://github.com/astrandb/weatherlink/releases/latest) [![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration) ![Validate with hassfest](https://github.com/astrandb/weatherlink/workflows/Validate%20with%20hassfest/badge.svg) ![Maintenance](https://img.shields.io/maintenance/yes/2023.svg) [![weatherlink_downloads](https://img.shields.io/github/downloads/astrandb/weatherlink/total)](https://github.com/astrandb/weatherlink) [![Weatherlink_downloads](https://img.shields.io/github/downloads/astrandb/weatherlink/latest/total)](https://github.com/astrandb/weatherlink)

# Weatherlink Integration for Home Assistant

This integration will represent your data from Davis Weaterlink in Home Assistant.
It will query the API every 5 minutes. The data update frequency in the API is depending on your subscription level. I e if you have the free "Basic" level, the observations data will only be updated every 15 minutes.

## Limitations

There are lots of combinations of station types and sensor types. Please report an issue here if you are missing something essential.

Current version has limited error detection and recovery and will therefore log detailed error descriptions if unforeseen things happen.


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

## Translation
To handle submission of translations we are using [Lokalise](https://lokalise.com/login/). They provide us with an amazing platform that is easy to use and maintain.

To help out with the translation of Miele integration  you need an account on Lokalise, the easiest way to get one is to [click here](https://lokalise.com/login/)  then select "Log in with GitHub".

When you have created the account, the [click here](https://app.lokalise.com/public/7686649965196d3196cb85.23152808/) to join the project. If you want to add a new language, please open an issue.

The translations are pulled when a new release of the integration is prepared. So you must wait until there is a new release until your look for your updates.

If you want to add new elements that needs translation you should enter them in /translations/en.json and submit a PR. The new keys will appear in Lokalise when the PR is merged.

## Disclaimer

The package and its author are not affiliated with Davis Instruments or Weatherlink. Use at your own risk.

## License

The package is released under the MIT license.

## Support and cooperation
This project is supported by

[<img src="https://raw.githubusercontent.com/astrandb/documents/fef0776bbb7924e0253b9755d7928631fb19d5c7/img/Lokalise_logo_colour_black_text.svg" width=120>](https://lokalise.com)
