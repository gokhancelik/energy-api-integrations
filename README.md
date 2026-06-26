# Dynamic Energy Prices

A Home Assistant custom integration for dynamic/real-time energy prices in the
Netherlands and Belgium, with a provider-pluggable architecture.

## Supported providers

| Provider | API Type | Auth | Electricity | Gas | Belgium |
|---|---|---|---|---|---|
| Essent (NL) | REST | None (header fix) | ✅ | ✅ | ❌ |
| EnergyZero (NL) | REST | None | ✅ | ✅ | ❌ |
| Eneco (NL) | REST (EnergyZero alias) | None | ✅ | ✅ | ❌ |
| Frank Energie (NL/BE) | GraphQL | None | ✅ | ✅ | ✅ |
| Vattenfall (NL) | — | — | ❌ | ❌ | ❌ |

Vattenfall TijdPrijs uses fixed time-of-use tariffs, not a real-time dynamic
pricing API — it cannot be implemented as a dynamic price provider.

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
3. Select your provider (Essent, EnergyZero, Eneco, or Frank Energie).
4. For Frank Energie: optionally toggle the Belgium region.
5. After setup, go to **Options** to configure a custom price threshold for
   the cheap electricity binary sensor (optional — defaults to today's average).
6. The integration will create sensors for current, next, average, lowest,
   and highest electricity prices, plus gas prices if available.

## Sensors

### Today's electricity prices

| Sensor | Description | Enabled by default |
|---|---|---|
| `current_electricity_price` | Current hourly electricity price | ✅ |
| `next_electricity_price` | Next upcoming hourly price | ✅ |
| `average_electricity_price` | Average of all 24 hourly prices today | ✅ |
| `lowest_electricity_price` | Lowest price today | ❌ |
| `highest_electricity_price` | Highest price today | ❌ |
| `cheapest_3h_block_electricity` | Cheapest contiguous 3-hour block (sliding window) | ❌ |
| `last_updated` | Timestamp of the last successful data refresh | ❌ |
| `next_update` | Scheduled time of the next data refresh | ❌ |

### Today's gas prices

| Sensor | Description | Enabled by default |
|---|---|---|
| `current_gas_price` | Current hourly gas price (if available) | ✅ |
| `next_gas_price` | Next upcoming gas price (if available) | ✅ |

### Tomorrow's prices

| Sensor | Description | Enabled by default |
|---|---|---|
| `tomorrow_average_electricity_price` | Average electricity price for tomorrow | ✅ |
| `tomorrow_lowest_electricity_price` | Lowest electricity price tomorrow | ❌ |
| `tomorrow_highest_electricity_price` | Highest electricity price tomorrow | ❌ |
| `tomorrow_average_gas_price` | Average gas price for tomorrow (if available) | ✅ |
| `tomorrow_lowest_gas_price` | Lowest gas price tomorrow (if available) | ❌ |
| `tomorrow_highest_gas_price` | Highest gas price tomorrow (if available) | ❌ |

### Breakdown sensors (disabled by default)

These sensors expose the components that make up the current electricity price.
The `current_electricity_market_price` sensor can be used as the
**Energy Dashboard Export Compensation** price entity.

| Sensor | Description |
|---|---|
| `current_electricity_market_price` | Raw market price component |
| `current_electricity_supplier_markup` | Supplier surcharge component |
| `current_electricity_energy_tax` | Energy tax component |

### Binary sensor

| Sensor | Description | Enabled by default |
|---|---|---|
| `cheap_electricity` | ON when the current price is below today's average price | ❌ |

### Extra attributes

Each sensor includes provider-specific attributes. The `current_electricity_price`
sensor includes a `price_breakdown` attribute with `market_price`,
`supplier_markup`, and `energy_tax` components.

The `cheap_electricity` binary sensor includes `current_price`,
`average_price`, and `threshold` attributes. The threshold can be set to a
custom value via **Configure** on the integration entry. When no custom
threshold is set, today's average price is used.

### Services

| Service | Target | Description |
|---|---|---|
| `force_update` | `sensor`, `binary_sensor` | Force refresh price data from the provider |

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

# Run tests for a specific module
pytest tests/test_sensor.py tests/test_binary_sensor.py -v
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
- [x] Eneco NL (EnergyZero alias provider)
- [x] Config flow with provider-specific options (Belgium toggle)
- [x] Belgium (BE) support toggle in Frank Energie config
- [x] Force-update service
- [x] Tomorrow's prices sensors
- [x] Standardised breakdown sensors (market price, supplier markup, energy tax)
- [x] Cheap electricity binary sensor (current < average)
- [x] Cheapest 3-hour block sensor (sliding window)
- [x] Options flow with custom threshold
- [x] Diagnostics sensors (last updated, next update)
- [ ] Repair/issue flow for API errors
- [ ] Diagnostics sensors (last updated, next update)
- [ ] Repair/issue flow for API errors

## Credits

Structural skeleton adapted from
[jaapp/ha-essent-dynamic](https://github.com/jaapp/ha-essent-dynamic) (MIT).
See [NOTICE](./NOTICE).

## License

MIT
