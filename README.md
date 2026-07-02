# Dynamic Energy Prices

[![Coverage Status](https://coveralls.io/repos/github/gokhancelik/energy-api-integrations/badge.svg?branch=main)](https://coveralls.io/github/gokhancelik/energy-api-integrations?branch=main)
[![Quality Scale](https://img.shields.io/badge/quality%20scale-platinum-%234285F4)](https://developers.home-assistant.io/docs/core/integration-quality-scale/)

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

Available for **EnergyZero**, **Eneco**, and **Frank Energie** (providers that
implement `async_fetch_prices_for_date`). Not created for **Essent** since it
does not offer a date-based API.

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

The `current_electricity_price` sensor includes:
- `price_breakdown` — `market_price`, `supplier_markup`, `energy_tax` components
- `hourly_prices` — list of `{start, end, price}` for all 24 hours of the day.
  Useful for custom Lovelace cards or Grafana.

The `cheapest_3h_block_electricity` sensor includes:
- `end_time` — end time of the cheapest block
- `average_price` — average price across the block
- `prices` — list of individual hourly prices in the block

The `cheap_electricity` binary sensor includes `current_price`,
`average_price`, and `threshold` attributes. The threshold can be set to a
custom value via **Configure** on the integration entry. When no custom
threshold is set, today's average price is used.

## Usage examples

### Cheapest 3‑hour block — time‑based automation

The sensor has `device_class: timestamp` — its state is the start time as a
datetime. Use it directly in automations:

```yaml
automation:
  - alias: "Run dishwasher at cheapest block"
    trigger:
      - platform: state
        entity_id: sensor.essent_cheapest_3h_block_electricity
    action:
      - delay:
          hours: 0  # fires immediately when cheapest block updates
      - service: switch.turn_on
        target:
          entity_id: switch.dishwasher
```

To start at the *beginning* of the block instead of immediately on update:

```yaml
automation:
  - alias: "Start charger at cheapest 3h block"
    trigger:
      - platform: template
        value_template: >
          {{ now().hour ==
             state_attr('sensor.essent_cheapest_3h_block_electricity', 'start_time')[0:2] | int
             and now().minute == 0 }}
    action:
      - service: switch.turn_on
        target:
          entity_id: switch.ev_charger
```

### Template sensor — cheapest block end time

```yaml
template:
  - sensor:
      - name: "Cheapest block end"
        state: >
          {{ state_attr('sensor.essent_cheapest_3h_block_electricity', 'end_time') }}
      - name: "Cheapest block average price"
        unit_of_measurement: "EUR/kWh"
        device_class: monetary
        state: >
          {{ state_attr('sensor.essent_cheapest_3h_block_electricity', 'average_price') }}
```

### Hourly prices in a template

```yaml
template:
  - sensor:
      - name: "Current hour price rank"
        state: >
          {% set prices = state_attr('sensor.essent_current_electricity_price', 'hourly_prices') %}
          {% set sorted = prices | sort(attribute='price') %}
          {% for p in sorted %}
          {% if p.start == now().strftime('%H:%M') %}
          {{ loop.index }} / {{ prices | length }}
          {% endif %}
          {% endfor %}
```

### Energy Dashboard export compensation

The `current_electricity_market_price` breakdown sensor provides the
pre-tax market rate and is the correct entity for the Energy Dashboard
**Export Compensation** price entity.

### Cheap electricity — automations

With the binary sensor enabled, you can trigger on state changes:

```yaml
automation:
  - alias: "Notify when electricity is cheap"
    trigger:
      - platform: state
        entity_id: binary_sensor.essent_cheap_electricity
        to: "on"
    action:
      - service: persistent_notification.create
        data:
          title: "Cheap electricity"
          message: >
            Price is {{ state_attr('binary_sensor.essent_cheap_electricity', 'current_price') }}
            (threshold {{ state_attr('binary_sensor.essent_cheap_electricity', 'threshold') }})
```

### Services

| Service | Target | Description |
|---|---|---|
| `force_update` | `sensor`, `binary_sensor` | Force refresh price data from the provider |

## Data updates

The integration polls your provider's API every **60 minutes** with a random
start-minute offset (0–59) to spread load evenly across users. Each request
has a **15-second timeout**. If a request fails, the coordinator keeps the
last successful data and retries on the next cycle.

After **3 consecutive failures** a repair issue is created in **Settings >
Repairs** with the error details. It is cleared automatically on the next
successful fetch.

## Supported features

- Real-time monitoring of current, next, average, lowest, and highest
  electricity and gas prices
- Breakdown sensors showing the market price, supplier markup, and energy tax
  components of the current electricity price
- Tomorrow price preview (for EnergyZero, Eneco, and Frank Energie)
- Cheapest 3‑hour block sensor with `device_class: timestamp` — state is the
  start time of the cheapest remaining block of the day
- Binary sensor that indicates when the current price is below a configurable
  threshold (defaults to the day's average price)
- Diagnostics sensors showing the last update time and next scheduled update
- Force‑update service to trigger an immediate refresh
- `hourly_prices` attribute on `current_electricity_price` with the full 24-hour
  price curve
- Multi‑provider support: run multiple config entries simultaneously
  (e.g., EnergyZero for electricity + Frank Energie for gas)

## Known limitations

- **Essent** does not offer a date-based API, so tomorrow-price sensors are
  not created for Essent config entries.
- **Vattenfall** TijdPrijs is a fixed time-of-use tariff, not a real-time
  dynamic price — it cannot be implemented as a dynamic price provider.
- The **cheapest 3‑hour block** only considers the remaining hours of the
  current day. It will not find a block if fewer than 3 hours are left until
  midnight.
- The **binary sensor** compares the current hour's price against the day's
  average. It uses the average of **all** 24 hours, so early in the day the
  average is less representative.
- Providers may return prices with different timezones. The integration uses
  the provider's native timezone where possible (e.g., `Europe/Amsterdam` for
  Essent).

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| No entities created after setup | API key issue or network | Check HA logs for `UpdateFailed` errors |
| Essent shows "401 Unauthorized" | Missing `x-request-origin` header (fixed in v0.8.1) | Update to the latest version |
| `'HomeAssistant' object has no attribute 'issues'` | HA version predates the issues API (pre-2023.6) | Update HA or ignore — no functional impact (fixed in v0.15.1) |
| Entity "no longer being provided" | Setup failed during refresh | Restart HA after updating to latest version |
| Tomorrow sensors missing | Provider does not support date-based queries (Essent) | Expected — not available for Essent |
| Gas sensors missing | Provider returned no gas data, or only electricity is available | Expected — check provider capabilities |
| Prices seem wrong / outdated | Data is polled every 60 minutes | Use the `force_update` service to trigger an immediate refresh |

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
- [x] Cheapest 3-hour block sensor (sliding window, TIMESTAMP device class)
- [x] Options flow with custom threshold
- [x] Diagnostics sensors (last updated, next update)
- [x] Repair/issue flow for API errors
- [x] Silver quality scale

## Credits

Structural skeleton adapted from
[jaapp/ha-essent-dynamic](https://github.com/jaapp/ha-essent-dynamic) (MIT).
See [NOTICE](./NOTICE).

## License

MIT
