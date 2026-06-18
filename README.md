# Dynamic Energy Prices

A Home Assistant custom integration for dynamic/real-time energy prices in the
Netherlands, with a provider-pluggable architecture.

## Supported providers

| Provider | API Type | Auth | Electricity | Gas | Belgium |
|---|---|---|---|---|---|
| Essent (NL) | REST | None (header fix) | ✅ | ✅ | ❌ |
| EnergyZero (NL) | REST | None | ✅ | ✅ | ❌ |
| Eneco (NL) | REST (EnergyZero alias) | None | ✅ | ✅ | ❌ |
| Frank Energie (NL/BE) | GraphQL | None | ✅ | ✅ | ✅ |

### Provider details

- **Essent** — Uses the `essent.nl` public pricing API. Requires a
  `x-request-origin: client` header (the official HA integration has been broken
  since 2026-06-03 because this header was not sent).
- **EnergyZero** — Uses the `api.energyzero.nl` public REST API. No
  authentication required.
- **Eneco** — Reuses the EnergyZero public API (white-label backend). Same
  features, listed separately for clarity.
- **Frank Energie** — Uses the `graphql.frankenergie.nl` public GraphQL API.
  No authentication required. Supports Netherlands (default) and Belgium
  (add `x-country: BE` header).

## Installation

### Via HACS (custom repository)

1. Ensure [HACS](https://hacs.xyz) is installed.
2. Go to **HACS > Integrations > Custom repositories**.
3. Add `https://github.com/gokhancelik/energy-api-integrations` as
   category **Integration**.
4. Click **Download** on the "Dynamic Energy Prices" integration.
5. Restart Home Assistant.

### Manual

1. Copy `custom_components/dynamic_energy_prices/` into your HA
   `custom_components/` directory.
2. Restart Home Assistant.

## Setup

1. Go to **Settings > Devices & Services > Add Integration**.
2. Search for "Dynamic Energy Prices".
3. Select your provider (Essent, EnergyZero, or Frank Energie).
4. The integration will create sensors for current, next, average, lowest,
   and highest electricity prices, plus gas prices if available.

No configuration is needed for providers that use public APIs. Provider-specific
options (e.g., Belgium region for Frank Energie) may be added in a future
release.

## Sensors

| Sensor | Description | Enabled by default |
|---|---|---|
| Current electricity price | Current hourly price | ✅ |
| Next electricity price | Next upcoming hourly price | ✅ |
| Average electricity price | Average of all today's prices | ✅ |
| Lowest electricity price | Lowest price today | ❌ |
| Highest electricity price | Highest price today | ❌ |
| Current gas price | Current hourly gas price (if available) | ✅ |
| Next gas price | Next upcoming gas price (if available) | ✅ |

Each sensor includes extra attributes: provider name, price breakdown
(market price, tax, surcharge, energy tax reduction).

## Adding a new provider

See [`providers/base.py`](custom_components/dynamic_energy_prices/providers/base.py)
for the `PriceProvider` ABC and dataclasses.

1. Create `custom_components/dynamic_energy_prices/providers/<name>.py`.
2. Subclass `PriceProvider`, set `provider_id` and `display_name`.
3. Implement `async_fetch_prices()` returning `ProviderPrices`.
4. Import the module in
   [`providers/__init__.py`](custom_components/dynamic_energy_prices/providers/__init__.py)
   for auto-registration. No other files need changes.

## Development

```bash
# Install test dependencies (Windows: pip install tzdata as well)
pip install -r requirements_test.txt

# Run all tests
pytest --asyncio-mode=auto -v

# Run tests for a specific provider
pytest tests/test_essent_provider.py -v
pytest tests/test_energyzero_provider.py -v
pytest tests/test_frank_energie_provider.py -v

# Smoke-test against live APIs
python scripts/smoke_test_essent.py
python scripts/smoke_test_energyzero.py
python scripts/smoke_test_frank_energie.py
```

## Roadmap

- [x] Essent provider
- [x] EnergyZero provider
- [x] Frank Energie provider (NL + BE)
- [x] Pluggable provider architecture
- [x] 42+ unit tests with CI (pytest, hassfest, HACS validation)
- [x] Eneco NL (EnergyZero alias provider)
- [ ] Vattenfall NL (TijdPrijs — time-of-use, no real-time API available)
- [ ] Config flow with provider-specific options (Belgium toggle, etc.)
- [ ] Belgium (BE) support toggle in Frank Energie config
- [ ] Release v0.2.0

## Credits

Structural skeleton adapted from
[jaapp/ha-essent-dynamic](https://github.com/jaapp/ha-essent-dynamic) (MIT).
See [NOTICE](./NOTICE).

## License

MIT
