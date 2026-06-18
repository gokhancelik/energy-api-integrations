"""Eneco dynamic energy price provider (EnergyZero white-label)."""

from __future__ import annotations

from .energyzero import EnergyZeroPriceProvider


class EnecoPriceProvider(EnergyZeroPriceProvider):
    """Provider for Eneco dynamic energy prices (runs on EnergyZero backend)."""

    provider_id = "eneco"
    display_name = "Eneco"
