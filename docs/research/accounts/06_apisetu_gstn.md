# API Setu - GSTN Tax Payer API (read 11 Nov 2026)

Source: API Setu's published OpenAPI spec https://cf-media.api-setu.in/specfiles/gstn.yaml ("GSTN Tax Payer API", 1.0.0,
updated 25 June 2021, terms https://apisetu.gov.in/terms.php). Used by `server/app/bahi/apisetu.py`.

- Call: `GET https://apisetu.gov.in/gstn/v1/taxpayers/{gstin}`; security = BOTH `X-APISETU-CLIENTID` and `X-APISETU-APIKEY`
  (the partner portal app's client id + API key).
- 200: gstin, legalName, constitution, registrationDate (DD/MM/YYYY), status, taxPayerType, centerJurisdiction, stateJurisdiction,
  cancellationDate (DD/MM/YYYY or ''), natureBusinessActivities[].
- Errors `{error, errorDescription}`: 400 invalid parameter / missing parameter; 401 invalid_authentication ("Authentication failed")
  / invalid_authorization ("You are not authorized to use this API" - the app is not subscribed to this API); 404 record_not_found;
  500 / 502 / 503 / 504.
- Not in the spec (so Hoola assumes nothing): a rate limit, a price, a sandbox. The spec gives no trade name or address.

What it is good for in BAHI: a free, official "is this GSTIN real and Active?" before a purchase bill is booked (input tax credit
on a cancelled supplier's bill is at risk), and ahead of the paid gstinapi.in `gstin_verify` in the API box. Not yet wired to either.
