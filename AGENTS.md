# AGENTS.md — Dynamic Energy Prices

## Architecture

- Single HA custom integration at `custom_components/dynamic_energy_prices/`
- Provider-pluggable: `PriceProvider` ABC with `__init_subclass__` auto-registration into `PROVIDER_REGISTRY`
- Domain: `dynamic_energy_prices`, `single_config_entry: false`, `integration_type: service`
- Add a provider: 1 file in `providers/` + 1 import in `providers/__init__.py`, no other files touched
- Vendored API clients in-repo (no upstream PyPI dependency for providers)

## Providers

| Provider | API | Auth requirement |
|---|---|---|
| Essent | REST GET `essent.nl/.../dynamic-prices/v1` | Header `x-request-origin: client` (401 without it) |
| EnergyZero | REST GET `api.energyzero.nl/v1/energyprices` | None — params: `fromDate`, `tillDate`, `interval=4`, `usageType=1\|3`, `inclBtw=true` |
| Eneco | REST (EnergyZero alias) | Same as EnergyZero (white-label backend) |
| Frank Energie | GraphQL POST `graphql.frankenergie.nl/` | None — query: `MarketPrices($date: String!)` |

## Tests

- 52 tests pass standalone (mocked HA via `conftest.py`); 11 tests require `pytest-homeassistant-custom-component` with real `hass` fixture (will ERROR, not fail)

```bash
pytest --asyncio-mode=auto -v                                      # all
pytest tests/test_<provider>.py -v                                 # single provider
```

### Test quirks

- `conftest.py` uses real Python dataclass bases (not `MagicMock`) for `SensorEntityDescription` etc. to avoid metaclass / dataclass inheritance conflicts
- EnergyZero provider makes 2 sequential `session.get()` calls (electricity + gas) — mock pattern uses `side_effect: list[AsyncMock]`
- `tzdata` required on Windows (`pip install tzdata`) for `ZoneInfo("Europe/Amsterdam")`
- Smoke scripts: only `scripts/smoke_test_essent.py` exists

## CI

- `.github/workflows/test.yaml` — pytest on push/PR (Python 3.12, 3.13, ubuntu-latest)
- `.github/workflows/validate.yaml` — hassfest + HACS validation on push/PR/daily cron
- No linter, formatter, pre-commit, or typechecker configured

## Release

- HACS integration type: `hacs.json` with `content_in_root: false`, no `filename` field
- Create a GitHub Release for HACS download
- Bump version in `custom_components/dynamic_energy_prices/manifest.json`
