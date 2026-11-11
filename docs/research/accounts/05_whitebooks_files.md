# WhiteBooks files the owner shared (11 Nov 2026)

Ten files from WhiteBooks, read on 11 Nov 2026. They are WhiteBooks' / the government's documents, so they are NOT committed here;
what Hoola uses from them is summarised below (and the error lists are kept as data in `server/app/bahi/wb_errors.json`).

## What they settle

| File | What it says | Used for |
|---|---|---|
| `whitebooks-gst-api-documentation.docx` | Sign-up steps: enable the account, create credentials, **then ask support to enable the sandbox account**; every parameter (`email`, `gst_username`, `state_cd` = first 2 digits of the GSTIN, `fy` YYYY-YY, `ret_period` MMYYYY, `txn` valid 6 h, `refid`, `ek`); the save -> status -> submit -> file (DSC) / EVC flow | A1 connect walk, A5 filing |
| `GST_API.postman_collection.zip` | Two files: an OpenAPI 1.0 spec and a Postman collection of **281 GST requests**; `/public/search` = query gstin + email, headers client_id / client_secret only; `/public/rettrack` = gstin + fy + type (R1) + email; `/authentication/authtoken` says "Default OTP for SandBox is 575757" | `bahi/wb.py` matches it (checked) |
| `E-INVOICE-API.postman_collection.zip` | 10 requests on `https://apisandbox.whitebooks.in`; authenticate = headers username, password, ip_address, client_id, client_secret, gstin | matches `wb.einv_auth` |
| `E-waybill.postman_collection.zip` | 26 requests; authenticate v1.03 = query username, password (+ email), headers ip_address, client_id, client_secret, gstin; the only reply example: `status_cd`, `status_desc`, `error{code, desc, error_cd, message}`, `data` | matches `wb.ewb_auth`; error fields read by `wb._code_of` |
| `e-Invoice-Ewaybill-Sandbox-Credentials.pdf` | One shared test GSTIN + username + password per state for e-invoice and e-way bill (Maharashtra 27AAGCB1286Q005 / BVMMH) - **no GST (returns) test account** | `wb_check` e-invoice + e-way bill logins PASS with it |
| `Return-Filing-through-API_v1.1.docx` | GSTN's return flows (GSTR-1 / 1A / 2 / 3 / 3B / 4 / 6): save -> status -> summary -> submit -> set off -> file; GSTR-3B has no submit; GSTR-4 save is all sections together | A5 / A6 |
| `Released_API_List_20231218.xlsx` | 365 GSTN APIs with sandbox / production versions + whether WhiteBooks offers each (e.g. Search Taxpayer v1.2, View and Track Returns v1.0, OTP / Auth Token v1.0) | phase planning |
| `GST-API-Error-Codes.docx` | 123 GSTN codes (RET114xx header / user / GSTIN, AUTH1xx, RET13509 OTP, RT_FIL_*, RET191xxx GSTR-1 data) | `wb_errors.json` -> `wb.known_error` |
| `E-invoicing-error-codes.docx` | 128 NIC IRP codes with message, reason and fix (2150 duplicate IRN, 2140 schema, 3xxx validations) | `wb_errors.json` |
| `e_Invoice_preparation_tools.xlsx` | Every INV-01 field with pattern, length, mandatory, sample; validation rules; master codes (states, units); B2B / export / SEZ JSON samples | A3 e-invoice builder |
| `e_Waybill_preparation_tools.xlsx` | Every e-way bill field with type, validation; master codes (supply / sub-supply / doc types, units, transport mode); supply x document type table; delivery challan + B2C samples | A4 e-way bill builder |

## Live result that these explain (wb_check 11 Nov 2026, 09:44 UTC)

Keys accepted, e-invoice + e-way bill sandbox logins PASS. GST public search answered "Public API Search Taxpayer Fail" and filing
track a bare refusal for 27AAGCB1286Q005 - the GST sandbox account is a separate switch-on by WhiteBooks support (the GST doc's
step 3), and the shared PDF has no GST test GSTIN / username. Next: WhiteBooks support enables the GST sandbox and gives its test
GSTIN + gst_username; then `WHITEBOOKS_SANDBOX_GST_USERNAME` (and a GST GSTIN line if it differs).
