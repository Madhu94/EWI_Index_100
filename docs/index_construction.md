#### Notes:

The goal of the assignment is to create a custom index consisting of large cap US stocks. The index will be adjusted daily, and rebalanced daily.

Adjusting an index means re-evaluating the components of the index based n current market cap data, and see if the top 100 have changed. If yes,
stocks ae added and/or removed from the index to ensure that the index holds top 100 market constituents.

It is important that changes to the index do not constitute jumps in the index value. A `divisor` is used to achieve this. (discussed later in this doc)

This is to be an *equal weighted index**, which means that each member stock contributes an equal notional value to the index composition. So even if the prices of the components change, their notional value (number of notional shares * price of each share) should be the same for each index member. 

This is where **rebalancing** comes in.  We adjust the number of notional shares so that each index member contributes equal notional value.

The term notional shares means that no actual shares are bought or sold in the process.

Each index has a base level (100 or 1000 usually) and a base date (creation of the index). We can arbitrarily keep base level = 1000, base date = June 2, 2025.

`Index Market Value` = Market value of its components (sum of price * number of notional shares for all members)
`Index Level/Value` = Index Market Value / Divisor.


This is an attempt to formalize an algorithm for rebalancing and adjusting daily, when the index consists of `N` stocks:

**Implemented algorithm (Incomplete)**
* On the base day, ensure to set weights (notional number of shares) such that index level / divisor = base value. 
* On each day, rebalance the index and then adjust it.
* When rebalancing, take the new changed value of the index and find the `new target value` (`new index value / N`).
* Set notional number of shares = `new target value / price`
* When adjusting, adjust the newly balanced index and add new stocks with a notional weight such that the contribution of the new stock also
equals the new target value.

**Questions**
Fractional shares?
* This approach would definitely lead to notional number of shares being a fraction. Even if it's possible to purchase fractional shares in a fund (fund managers pool fractions to a whole), in this case, it would be ideal to use approximately whole numbers since Indexes are usually
replicated by fund managers and arbitrary fractional weights can be less meaningful here.
* The above algorithm would also ensure divisor = 1 in each case.
* One alternative working approach (if not optimal one) to deal with this could be to set target to be approx. equal to LCM of the prices of all the new components, and use the divisor to prevent index jumps.

It would be good to get a working example/excel of how this is done in practice. 


**[TODO] Corporate actions**
<WIP>