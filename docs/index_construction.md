#### Notes:

* The index we create will be a **large cap index**, consisting of 100 top US stocks by market capitalization (free float).
* Indexes start off with a base value, a base date, and an initial notional number of shaes of each of its constituents.
* `Notional shares` means no real shares are bought or sold here.
* We can keep base level = 1000, base date = June 2, 2025.
* Index Value = Market value of its components (sum of price * number of notional shares for all members)
* Index Level = Index Value / Divisor (Divisor is discussed later)
* **Adjusting the index** is where stocks' market cap is reviewed based on recent price and shares_outstanding data. New stocks may be added and existing stocks may be removed.
* Changes to the index membership should not cause jumps in the index value, hence a divisor is created which will determine index level between adjustments.
* **Equal weighted indexes** ensure that each member stock contributes an equal notional value to the index composition.
This means the notional number of shares are changed to ensure this, as the price of the members changes.
* Adjusting and rebalancing the index is to take place daily.
