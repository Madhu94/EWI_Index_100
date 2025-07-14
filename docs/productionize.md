### Data acquisition

#### API Changes

**Current state**
* FMP's Free tier API has rate of 250 reqs/day for batch. This would not suffice for entire US data. Free tier API also provides only latest market cap data and not historical. For the purpose of the assignment, this was worked around by pulling data for a month and assuming shares_outstanding doesn't change all that much in that time. Hence shares_outstanding for a day = latest market cap / price on that day.

**Moving to production**
* **API Evaluation** -  FMP (Financial Modelling Prep) API is used to fetch historical prices and market cap data for US Stocks. Based on the evaluation, both Polygon and FMP free tiers had the same capabilities for this particular use case and similar rate limit issues. For purpose of this assignment, I picked FMP as it had a bulk endpoint for historical prices in free tier.

For usage in production, where the free tier rate limits would not be acceptable, a decision has to be made by evaluating the paid offerings on criteria such as cost of the API vs budget of the project, rate limits, licensing agreements, and other constraints projects has to comply with.

* **API Key** - Use a secret management tool like Vault to ensure API keys are kept safely.

* **Move out of free tier** - Use entire stock data instead of a hardcoded universe of 10 stocks. This involves switching over to paid version of FMP API to fetch historical market cap data.

* **Code changes** - To incorporate the above point, the MarketDataFetcher class can be changed without any change to outside code. The same advantage holds if we decide to use some API other than FMP - we can just change MarketDataFetcher. Update INDEX_SIZE to 100.

* **Batch runner**: 
To run the data ingestion job daily. Some thoughts on deciding how to pick this:

* FastAPI's background jobs feature or Linux Cron won't be adequate as we would need retries, monitoring, etc and the use case is very critical.
* More feature-rich scheduling tools like AirFlow & Celery may be overkill just for the specific case of running a single job daily. However, it may be desirable to pick them if the team already relevant infrastructure and expertise. 
* For a fresh project with a simple but critical cron job like this, APScheduler provides the right balance of simplicity and scaling down as well as scaling up. Would recommend this choice.

* **Dockerfile inputs** - Another point to address would be to read the date for ingest script from env vars, instead of hardcoding for the June month.

### Web app Deployment

**Current State**
* FastAPI's dev server is used, which starts up uvicorn as ASGI Server

**Moving to production**

* **HTTPS** - Setup SSL certificates for the server domain name. LetsEncrypt would provide automated renewal. Web servers like Nginx would support auto-verification through plugins.
* **Reverse Proxy** - Nginx, for TLS Termination, connection management, rate limiting. If we were deploying on cloud, we can use what the cloud provider supports (like AWS API Gateway).  
* **ASGI Server** - Uvicorn or Gunicorn, depending on our deployment environment. Uvicorn with single worker would be best with an orchestrator which will handle replication. Otherwise, Gunicorn working as a process manager with uvicorn workers.
* **Logging** 
* **Auth & Rate limiting** - API key support and rate limiting per client. The authentication model needs to be discussed based on the use case.

### Database
**Current State**
* SQLite is used. Schema stores state of index each day and also changes separately keeping them both in sync.

**Moving to production**
* **Move to Client/Server database** SQLite would not be suitable due to single-file in-process usage model and lack of any replication strategies. Postgres/MySQL would be a good choice offering a client server model, with replication.
* **Configuration module** - Currently database name is inside the code.
* **Indexes** - For the `marketdata` table, we only pick the top 100 stocks. An index on the price * shares_outstanding expression could speed this up by avoiding a DB Scan.
* **Leverage aiosqlite** - Use aiosqlite to leverage improved concurrency of the ASGI server.
* **Schema Model** - 
    - `REBALANCE` events in changes can have more information on the changed weights too 
    - Instead of maintaining per day snapshot and aggregated version, an alternative model where we log just the changes and construct a materialized view out of aggregating the changes table (the idea behind event sourcing). We can save snapshots of aggregated state in the materialized view, and the API layer can just read the aggregated state or read closest (snapshot) aggregated state + relevant changes and arrive at a new state. This can save space in case our index does not change a lot. It also makes the changes table the source of truth and the aggregated state (index and constituents) as a derived data.


### Redis

**Current State**
* Default setting of noeviction.
* Single redis instance
* RDB snapshot persistance with default interval.


**Moving to production**
* **Deployment**: The access pattern is read heavy, with higher likelihood of accessing recent index returns. A good default might be to cache 1 month data by default. If the data does fit in memory, we can use Redis Sentinel mode, if not, we can use Redis Cluster.
* **Persistance**: RDB Files with periodic snapshot uploaded to S3.
* **Eviction**: Two choices we can consider are LRU, and caching last N days data. LRU could be a good default but it's possible the occasional rare request accessing old data could evict the data for more common requests for recent data. Caching last N days always would be better for this use case.



### Miscellaneous

* NYSE / Custom Trading Calendar support instead of just weekdays.
* Data Alerts