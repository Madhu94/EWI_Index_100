## Implemnetation notes

* Data Acquisition

Sample API for pulling price and market cap data

```
Pull price data (batch)
https://financialmodelingprep.com/api/v3/historical-price-full/AAPL,MSFT,GOOG,V,NVDA?from=2024-06-01&to=2024-06-30&apikey=<Your API Key>


Pull Market cap (latest)
https://financialmodelingprep.com/api/v3/profile/AAPL,MSFT,GOOG,V,NVDA,TSLA,META,AMZN,JPM,UNH?apikey=<Your API Key>

```

## Running the App


### API Key
* Register in https://site.financialmodelingprep.com/register (or login if you have account)
* Go to https://site.financialmodelingprep.com/developer/docs/dashboard
* You can copy your API key under "API Keys" section
* Set this in .env file in folder where you will run docker compose

```
echo API_KEY=YOUR API KEY > .env

```

### Run app

1. Start Docker, in case you don't have docker daemon running as service by default.

```
sudo systemctl docker start

```

2. Initialize the database.

```
docker compose --profile reset up --build

```

```
docker compose --profile init up --build

```

First command can be skipped if the database doesn't exist.
The above commands need sudo permissions if rootless docker is not used and if you
are not a member of docker user group.

3. Run Data Ingestion.

```
docker compose --profile ingest up --build

```

4. Start the FastAPI app & Redis. Ensure no sevices in the host system are running on ports
6379 and 8000.

```
docker compose --profile dev up --build

```

FastAPI endpoints would be exposed on http://0.0.0.0:8000/docs.

## API Invocations
(Dev mode - no auth)

1. Build and construct index

```
curl 'http://0.0.0.0:8000/build-index?start_date=2025-06-02&end_date=2025-06-05' \
  -X 'POST' \
  -H 'Accept-Language: en-GB,en-US;q=0.9,en;q=0.8' \
  -H 'Connection: keep-alive' \
  -H 'Content-Length: 0' \
  -H 'Origin: http://0.0.0.0:8000' \
  -H 'Referer: http://0.0.0.0:8000/docs' \
  -H 'User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36' \
  -H 'accept: application/json' \
  --insecure

```

2. Fetch Index & Membership details

```
curl 'http://0.0.0.0:8000/index-composition/?start_date=2025-06-02&end_date=2025-06-02' \
  -H 'Accept-Language: en-GB,en-US;q=0.9,en;q=0.8' \
  -H 'Connection: keep-alive' \
  -H 'Referer: http://0.0.0.0:8000/docs' \
  -H 'User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36' \
  -H 'accept: application/json' \
  --insecure

```

3. Fetch changes in Index composition

```
curl 'http://0.0.0.0:8000/composition-changes/?start_date=2025-06-02&end_date=2025-06-03' \
  -H 'Accept-Language: en-GB,en-US;q=0.9,en;q=0.8' \
  -H 'Connection: keep-alive' \
  -H 'Referer: http://0.0.0.0:8000/docs' \
  -H 'User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36' \
  -H 'accept: application/json' \
  --insecure

```

4. Compute Index Returns

```
curl 'http://0.0.0.0:8000/index-performance/?start_date=2025-06-03&end_date=2025-06-04' \
  -H 'Accept-Language: en-GB,en-US;q=0.9,en;q=0.8' \
  -H 'Connection: keep-alive' \
  -H 'Referer: http://0.0.0.0:8000/docs' \
  -H 'User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36' \
  -H 'accept: application/json' \
  --insecure

```

5. Export to excel

```
curl 'http://0.0.0.0:8000/export-data/?start_date=2025-06-02&end_date=2025-06-04' \
  -X 'POST' \
  -H 'Accept-Language: en-GB,en-US;q=0.9,en;q=0.8' \
  -H 'Connection: keep-alive' \
  -H 'Content-Length: 0' \
  -H 'Origin: http://0.0.0.0:8000' \
  -H 'Referer: http://0.0.0.0:8000/docs' \
  -H 'User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36' \
  -H 'accept: application/json' \
  --insecure

```



## Design Doc

See [here](docs/design.md)

## Productionization notes

See [here](docs/productionize.md)