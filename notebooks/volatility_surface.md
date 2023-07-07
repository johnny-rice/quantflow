---
jupytext:
  text_representation:
    extension: .md
    format_name: myst
    format_version: 0.13
    jupytext_version: 1.14.7
kernelspec:
  display_name: Python 3 (ipykernel)
  language: python
  name: python3
---

# Volatility Surface

In this notebook we illustrate the use of the Volatility Surface tool in the library. We use [deribit](https://docs.deribit.com/) options on BTCUSD as example.

First thing, fetch the data

```{code-cell} ipython3
from quantflow.data.client import HttpClient
deribit_url = "https://test.deribit.com/api/v2/public/get_book_summary_by_currency"
async with HttpClient() as cli:
    futures = await cli.get(deribit_url, params=dict(currency="BTC", kind="future"))
    options = await cli.get(deribit_url, params=dict(currency="BTC", kind="option"))
```

```{code-cell} ipython3
from decimal import Decimal
from quantflow.options.surface import VolSurfaceLoader
from datetime import timezone
from dateutil.parser import parse

def parse_maturity(v: str):
    return parse(v).replace(tzinfo=timezone.utc, hour=8)
    
loader = VolSurfaceLoader()
for future in futures["result"]:
    if (bid := future["bid_price"]) and (ask := future["ask_price"]):
        maturity = future["instrument_name"].split("-")[-1]
        if maturity == "PERPETUAL":
            loader.add_spot(future, bid=Decimal(bid), ask=Decimal(ask))
        else:
            loader.add_forward(parse_maturity(maturity), future, bid=Decimal(bid), ask=Decimal(ask))

for option in options["result"]:
    if (bid := option["bid_price"]) and (ask := option["ask_price"]):
        _, maturity, strike, ot = option["instrument_name"].split("-")
        call = ot == "C"
        bid = Decimal(bid)
        ask = Decimal(ask)
        loader.add_option(Decimal(strike), parse_maturity(maturity), call, option, bid=Decimal(bid), ask=Decimal(ask))
    
```

Once we have loaded the data, lets create the surface and display the term-structure of forwards

```{code-cell} ipython3
vs = loader.surface()
vs.term_structure()
```

This method allows to inspect bid/ask for call options at a given cross section

```{code-cell} ipython3
vs.options_df(index=2)
```

```{code-cell} ipython3
vs.bs(index=2).options_df(index=2)
```

```{code-cell} ipython3
len(r)
```

```{code-cell} ipython3

```