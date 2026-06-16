# Dynamic Energy Prices

A Home Assistant custom integration for dynamic/real-time energy prices, with a
provider-pluggable architecture. **Essent** is the first supported provider.

## Why this integration?

The official Home Assistant Essent integration has been broken since 2026-06-03
because Essent's public pricing API now requires a `x-request-origin: client`
header. The fix exists upstream but has not been merged or released.

This integration:

- Ships the header fix **today** without waiting for upstream.
- Is **provider-pluggable** so other energy providers can be added as peers.
- Is maintained independently via HACS, not tied to HA core's release cadence.

## Supported providers

| Provider | Status |
|---|---|
| Essent (NL) | ✅ Working |

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
3. Select your provider (e.g., **Essent**).
4. The integration will create sensors for current, next, average, lowest,
   and highest electricity prices, plus gas prices if available.

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

See [custom_components/dynamic_energy_prices/providers/base.py](custom_components/dynamic_energy_prices/providers/base.py).

1. Create a new file `custom_components/dynamic_energy_prices/providers/<name>.py`.
2. Subclass `PriceProvider`, set `provider_id` and `display_name`.
3. Implement `async_fetch_prices()` returning `ProviderPrices`.
4. The provider is auto-registered; no other files need changes.

## Development

```bash
# Install test dependencies
pip install -r requirements_test.txt

# Run tests
pytest --asyncio-mode=auto -v

# Smoke-test the Essent provider against the live API
python scripts/smoke_test_essent.py
```

## Credits

Structural skeleton adapted from
[jaapp/ha-essent-dynamic](https://github.com/jaapp/ha-essent-dynamic) (MIT).
See [NOTICE](./NOTICE).

## License

MIT
