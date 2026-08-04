# AGENTS.md — Dynamic Energy Prices

## Architecture

- Single HA custom integration at `custom_components/dynamic_energy_prices/`
- Provider-pluggable: `PriceProvider` ABC with `__init_subclass__` auto-registration into `PROVIDER_REGISTRY`
- Add a provider: 1 file in `providers/` + 1 import in `providers/__init__.py`, no other files touched
- Vendored API clients in-repo (no upstream PyPI dependency)
- Alias providers (e.g. Eneco → EnergyZero) subclass the parent provider, override only `provider_id` + `display_name`
- **Hourly sync timer:** coordinator fires `async_update_listeners()` at each local `:00` hour boundary, so sensor state changes (`last_changed`) align with actual price slot transitions, not with the randomized coordinator refresh offset.

## Providers

| Provider | API | Auth | Tomorrow data |
|---|---|---|---|
| Essent | REST GET `essent.nl/.../dynamic-prices/v1` | Header `x-request-origin: client` (401 without it) | Cached from multi-day response (yesterday + today + tomorrow) |
| EnergyZero | REST GET `api.energyzero.nl/v1/energyprices` | None | Separate API call per date |
| Eneco | REST (EnergyZero alias) | None | Same as EnergyZero |
| Frank Energie | GraphQL POST `graphql.frankenergie.nl/` | None | Separate API call per date |

## Tests

```bash
pytest --asyncio-mode=auto -v                          # all (182+ standalone tests)
pytest tests/test_<name>.py -v                         # single provider
pytest tests/ -k "not config_flow and not coordinator and not init"  # skip HA-fixture tests
```

### Test quirks

- `conftest.py` conditionally mocks `homeassistant` **only when** `pytest-homeassistant-custom-component` is absent. On CI (where it's installed), the real `hass` fixture is used instead.
- EnergyZero/Eneco providers make 2 sequential HTTP calls (electricity + gas). Mock pattern uses `side_effect: list[AsyncMock]` with `_make_mock_response` helper.
- `tzdata` required on Windows (`pip install tzdata`) for `ZoneInfo("Europe/Amsterdam")`.
- **Don't install `pytest-aiohttp`** — it causes thread-cleanup errors. Use `pytest-asyncio` with `pytest-homeassistant-custom-component`.
- 6 config_flow + 3 coordinator + 2 init tests need real `hass` fixture from `pytest-homeassistant-custom-component`; they fail if it's not installed.
- Essent `async_fetch_prices_for_date` is server from cache (no extra HTTP call). Call `async_fetch_prices()` first to populate the cache.
- Smoke scripts: only `scripts/smoke_test_essent.py` exists.

## CI / Validation

- `.github/workflows/test.yaml` — pytest on push/PR (Python 3.12, 3.13)
- `.github/workflows/validate.yaml` — hassfest + HACS validation
- **hassfest** requires `manifest.json` keys in order: `domain`, `name`, then alphabetically (a common fail).
- **HACS** requires:
  - `hacs.json` with `content_in_root: false`, no `filename` field
  - Brand icon at `custom_components/<domain>/brand/icon.png`
  - GitHub repo must have at least one HACS-relevant topic (`hacs`, `home-assistant`, etc.)
- No linter, formatter, pre-commit, or typechecker configured.

## Release

```bash
# Bump version, then:
git add custom_components/dynamic_energy_prices/manifest.json
git commit -m "Bump version to X.Y.Z"
git tag vX.Y.Z
git push && git push origin vX.Y.Z
gh release create vX.Y.Z --title "vX.Y.Z" --notes-file AGENTS.md
```

- Token auth for HTTPS git: `git -c "http.extraheader=Authorization: basic $(..." push`
- GitHub PAT format for git: username = `x-oauth-basic`, password = PAT

## Changelog

### v0.22.0

- **Restore full multi-day `hourly_prices` curve (fixes #2):** v0.17 split Essent's multi-day API response per-date, so `hourly_prices` on `current_electricity_price` shrank from 72 entries (yesterday+today+tomorrow, as in v0.16) to 24. It now spans all available days again for every provider: **yesterday+today+tomorrow** for Essent, **today+tomorrow** for EnergyZero/Eneco/Frank.
  - The value/computation sensors (`current`, `next`, `average`, cheapest block) intentionally stay **today-only** and stable (the v0.20.0 cheapest-block guarantee is preserved).
  - Implemented via a new `coordinator.all_electricity_prices` merged series + a `provides_yesterday_data` provider capability flag (True only on Essent, so other providers make no extra API calls).

### v0.21.0

- **Auto-installable, provider-aware dashboard:** The integration can now build and install a Lovelace dashboard at runtime (`dashboard.py`), resolving each configured entry's real entity IDs from the entity registry (so renames are respected) and emitting only the cards for the sensors a given provider/tariff actually creates.
  - Trigger it from the options flow (tick *Install or update the Energy Prices dashboard*) or via the new `dynamic_energy_prices.install_dashboard` service.
  - Multiple config entries are merged into one *Energy Prices* dashboard (`url_path: energy-prices`) with a tab per provider.
  - The `apexcharts-card` price-curve card is optional and off by default, controlled per entry by the `include_price_curve` option.
  - YAML-mode Lovelace is detected; `save_dashboard` returns False and the caller can fall back to `examples/dashboard.yaml` / `dashboard_to_yaml` (the service just logs a warning).
  - `examples/dashboard.yaml` remains as a static YAML-mode fallback reference.

### v0.20.0

- **Fix cheapest 3h block sensor shifting every hour:** The cheapest block was recomputed on the remaining future hours at every refresh, so the result crept forward hourly and went `unknown` late at night. It's now computed once from the full day's price data and stays stable until the next day's data arrives.

### v0.19.0

- **Restore long-term statistics for price sensors:** Dropped `device_class=MONETARY` from all price sensors and added `state_class=MEASUREMENT` instead. `MONETARY` only allows `state_class=TOTAL` in HA, but these are rates (prices per unit), not balances — so `MONETARY` was the wrong device class. Sensors now use the native unit from the provider (e.g. `EUR/kWh`) without monetary formatting.

### v0.18.0

- **Fix 500 error on options flow:** Removed `async` from `async_get_options_flow` — HA's flow manager doesn't `await` it, causing `AttributeError: 'coroutine' object has no attribute 'hass'`.
- **Fix state_class warnings:** Removed `state_class=MEASUREMENT` from all monetary sensors — HA 2026.6+ requires `device_class='monetary'` to have state_class `None` or `'total'`.

### v0.17.0 (broken — released and deleted)

- **Hourly sync timer:** Coordinator now fires sensor state updates at each local `:00` hour boundary. Sensor `last_changed` timestamps now align with actual price slot transitions instead of the randomized coordinator refresh offset.
- **Essent multi-day response:** Essent API returns yesterday + today + tomorrow prices in a single call. `async_fetch_prices_for_date` now serves tomorrow data from cache — no extra HTTP call.
- **Removed dead code:** Removed unused `randomized_minute` / `next_hour` randomization from coordinator init (was never applied).
