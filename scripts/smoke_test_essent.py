#!/usr/bin/env python3
"""Smoke test: hit the real Essent API and print the JSON response.

Run with: python scripts/smoke_test_essent.py

Requires: aiohttp
  pip install aiohttp
"""

from __future__ import annotations

import asyncio
import json
import sys

import aiohttp

API_ENDPOINT = "https://www.essent.nl/api/public/dynamicpricing/dynamic-prices/v1"
HEADERS = {
    "Accept": "application/json",
    "x-request-origin": "client",
}


async def main() -> None:
    """Fetch Essent prices and display results."""
    print(f"Fetching {API_ENDPOINT} ...")
    print(f"Headers: {HEADERS}")
    print()

    timeout = aiohttp.ClientTimeout(total=15)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(API_ENDPOINT, headers=HEADERS) as response:
            print(f"HTTP {response.status}")
            for key, value in response.headers.items():
                if key.lower() in ("content-type", "content-length", "x-"):
                    print(f"  {key}: {value}")
            print()

            if response.status == 200:
                data = await response.json()
                print(json.dumps(data, indent=2, default=str))
            else:
                text = await response.text()
                print(text[:2000])


if __name__ == "__main__":
    asyncio.run(main())
