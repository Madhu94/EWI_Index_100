
**Design notes**

**Business Models and Pydantic**
* The entire business logic is built using pydantic which serve as the business layer this includes index creation, adjustment, rebalancing, checking changes. 
* Apart from playing well with FastAPI, Pydantic models do well as the business domain classes themselves, enforcing type checking and contracts among the different utilities.
* The core models are 
   - **Stock** - which includes ticker, price, shares_outstanding, market cap (computed property).
   - **Index Member** - A member of the custom equal weighted index. Incorporates a Stock and a notional number of shares of the Stock
   - **EWIIndex100** - Index data for a given day, along with members. Index level is a computed property.
   - **IndexOperation** - Represents the kind of change that can happen to an index composition.
    * `ADD` - a new stock is added to the index, when its market cap is among
    the top 100 stocks by market cap.
    * `REMOVE` - a stock which is part of the index is removed, when its market
    cap is no longer among the top 100 stocks by market cap
    * `REBALANCE` - a stock which is part of the index has its notional number
    of shares adjusted so that it contributes an equal notional value to the index
   - **Change** - Represents an IndexOperation on a given date on a particular Stock.
* All the utilities for working with an index are modelled as functions which take in Index Models and return Index models. These ae completely immutable operations.
* See `compose.py`, `models.py`
* `returns.py` which has logic for computing daily and cumulative returns also works with pydantic models.

**Persistance & Data Model** 
* `redis.py` and `db.py` which access the database and cache respectively.
* These utilities read from the database and return pydantic models, or take in a pydantic model and write to the database.
* For persistance, we use SQLAlchemy Core for building expressions and SQLAlchemy Engine for managing connections.
* Database Model - 
    * **Marketdata** - Stores price and shares outstanding data for stocks for each date.
    * **IndexLevels** - Stores date, index, index level, divisor.
    * **Members** - Stores members of the index for each date, and their notional weights
    * **Changes** - Stores changes for each date if applicable.
* See `db/init.sql` for the DDL Statements.
* `redis.py` manages utilities for connecting to redis, bulk reads and bulk writes.

**FastAPI**
* `app.py` has the routes for all the endpoints

**Docker Compose**
* Services for FastAPI and Redis under the docker profile `dev`.
* init.sql for setup of db is run under `init`, even if sqlite isn't a service.
* wipe.sql for resetting the database if needed in dev setup, should be disabled in prod.
* Fetching market data in Dockerfile.ingest.
