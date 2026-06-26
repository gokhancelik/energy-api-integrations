"""Constants for the Dynamic Energy Prices integration."""

DOMAIN = "dynamic_energy_prices"

CONF_PROVIDER = "provider"
CONF_COUNTRY = "country"

DEFAULT_SCAN_INTERVAL_MINUTES = 60
DEFAULT_CURRENCY = "EUR"
DEFAULT_UNIT_ELECTRICITY = "EUR/kWh"
DEFAULT_UNIT_GAS = "EUR/m³"

SERVICE_FORCE_UPDATE = "force_update"

ATTR_CURRENT_PRICE = "current_price"
ATTR_NEXT_PRICE = "next_price"
ATTR_AVERAGE_PRICE = "average_price"
ATTR_LOWEST_PRICE = "lowest_price"
ATTR_HIGHEST_PRICE = "highest_price"
ATTR_PRICE_BREAKDOWN = "price_breakdown"
ATTR_PROVIDER = "provider"
ATTR_THRESHOLD = "threshold"
ATTR_LAST_UPDATED = "last_updated"
ATTR_NEXT_UPDATE = "next_update"


