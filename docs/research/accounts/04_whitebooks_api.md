# Accounts Assistant research 04 - the WhiteBooks GST / e-Invoice / e-Way Bill API (implementation grade, 11 Nov 2026)

The owner holds WhiteBooks API access. WhiteBooks = BVM IT Consulting Services India Pvt Ltd, a GSTN-licensed GSP; gateway product "I-HUB".

## 0. Which WhiteBooks pages to trust
- **The REAL contract = the OpenAPI 3.0 specs embedded in the Developer Hub** (`developer.whitebooks.in`, a React app):
  `assets/gst-api-Dg40VqhG.js` (284 operations), `assets/e-invoice-api-qnrG8gEK.js` (11), `assets/e-way-bill-api-B3XJyHAb.js` (27); the
  same specs are rendered per endpoint under `whitebooks.in/developer/...` (see `whitebooks.in/sitemap.xml`). Build to these.
- **The prose guides / marketing / FAQ describe a DIFFERENT API** (OAuth client-credentials, 1-hour bearer token, `x-api-key`,
  `POST /gst/authenticate`, HTTP 4xx codes, `GSTIN_INVALID` / `DUPLICATE_IRN`, webhooks, SDKs `@whitebooks/node` in five languages). The
  specs put `client_id` + `client_secret` as plain headers on every call with no token endpoint; **the live server agrees with the specs**
  (unauthenticated probes, no credentials used): every real path on `apisandbox.whitebooks.in` answers **HTTP 200** with
  `{"status_cd":"0","status_desc":"WB_ERR_9001 : Invalid credentials provided or your account is not active"}`; an unknown path HTTP 500
  `{"errorCode":"WB_ERR_9000",...}`; `@whitebooks/node` (npm) and `whitebooks` (PyPI) do not exist. **Treat OAuth / bearer / x-api-key /
  webhook / SDK / HTTP-status claims as UNVERIFIED** and confirm with WhiteBooks support using the sandbox keys.
- Roots: `https://apisandbox.whitebooks.in/` and `https://api.whitebooks.in/` both answer `{"message":"I-HUB is up and running!","version":"2.0.0"}`.

## 1. API families (VERIFIED in the specs)
- **GST**: Public (`/public/search` GSTIN search, `/public/searchbypan`, `/public/rettrack` filing track by FY, `/public/pref` QRMP
  preference, unregistered applicants); Authentication (OTP request, auth token, refresh, logout, OTP for EVC); Returns GSTR-1, 1A, 2A, 2B
  (incl. generate-on-demand), 2X, 3B (save / offset / file / interest / auto-liability / RCM + ITC-reversal opening balances), 4, 4A, 4
  annual, 5, 6, 6A, 7, 8, 9, 9A, 9C (incl. hash generator + certificate); **IMS** (save, reset, status, invoices, count, supplier invoices,
  rejected / added-back, getfile); ITC-03, ITC-04, CMP-08; SPIKE DRC-01B / 01C (1 vs 3B mismatch); ALL (proceed-to-file, return status, late
  fee, file details / large file, documents, masters, preference); Payment (PMT-06 challan, history / summary); Ledgers (cash, ITC,
  liability, balance, tax payable, blocked ITC, reversal / reclaim, negative liability, RCM statement, utilise cash / ITC); e-invoice data
  as GSTN sees it (IRN list, IRN JSONs, HSN summary); Notices (list, details).
- **e-Invoice (IRP, NIC v1.03 paths)**: authenticate, generate IRN, cancel IRN, get IRN, get IRN by document details, rejected IRNs,
  generate / get EWB by IRN, GSTN details, sync GSTIN from CP, B2C QR code.
- **e-Way Bill (NIC EWB v1.03)**: authenticate, generate, Part-B / vehicle update, consolidated (generate / regenerate / trip sheet),
  cancel, reject, update transporter, extend validity, closure, multi-vehicle (initiate / add / change), get EWB + lists (date / transporter /
  state / GSTIN / other party / rejected / by consigner document), transporter / GSTIN / HSN details, error list.
- **NOT in any spec: TDS, ITR, bank, KYC.** The only HSN lookup is EWB `gethsndetailsbyhsncode`.

## 2. Environments + onboarding
| | Sandbox | Production |
|---|---|---|
| Base URL | `https://apisandbox.whitebooks.in` | `https://api.whitebooks.in` |
| Data | test, no real filings | live GSTN / NIC |
| Cost | free | by plan |
| Rate limit | **60 req/min** (Quickstart) | by plan |
Developer sign-up `https://accounts.whitebooks.in/signup?type=Developer`; the Hub's Credentials page shows per product (gst / einvoice /
eway) the sandbox base URL, sandbox `client_id` / secret, **a sandbox GSTIN**, sandbox logins (username + password) and an OTP; production
keys "unlock with a subscription"; production needs KYC + a signed agreement (FAQ, "median 5 business days", partly UNVERIFIED); an "Auth
keys" page lists production usernames per product (likely each taxpayer user registered under the account - UNVERIFIED).
**Every endpoint takes a required `email` query parameter** = the WhiteBooks developer account email. **Every taxpayer-side call needs an
`ip_address` header** (the end user's IP, GSTN's ip-usr - inferred). IP allow-listing on production: prose only, UNVERIFIED.

## 3. Authentication (VERIFIED from the specs unless marked)
- **All calls**: headers `client_id`, `client_secret`; query `email`. No bearer token (the spec references `security: OAuth2` but defines no scheme).
- **GST (taxpayer) - the OTP flow** (the taxpayer must first enable API access on the portal, section 7):
  1. `GET /authentication/otprequest?email=` + headers `gst_username, state_cd, ip_address, client_id, client_secret` -> the GST system sends
     the OTP to the taxpayer's registered email + mobile.
  2. `GET /authentication/authtoken?email=&otp=` + headers `gst_username, state_cd, ip_address, txn, client_id, client_secret`.
     **Sandbox OTP = 575757.** `txn` is almost certainly the transaction id from the OTP-request response (UNVERIFIED - no response examples).
  3. `GET /authentication/refreshtoken` (same headers incl. `txn`) - extends access without the user; `GET /authentication/logout`.
  - Every later GST call: headers `gst_username, state_cd, ip_address, txn, client_id, client_secret`; GETs take query `gstin` +
    `retperiod` (MMYYYY) / `returnperiod` / `rtnprd` / `fy` (endpoint-specific) + `email`; save / file calls take HEADERS `gstin` +
    `ret_period` with `email` (+ `pan` / `evcotp` for filing) in the query. **No auth-token header: WhiteBooks holds the GSTN token
    server-side**, keyed by account + `gst_username` + `txn` (inferred). Lifetimes undocumented: GSTN token usually 6 h, extendable up to
    the taxpayer's chosen Manage-API-Access duration (6 h - 30 days); call refreshtoken periodically, re-OTP on failure.
  - `state_cd` = 2-digit state code of the GSTIN; `gst_username` = her GST portal username.
- **e-Invoice**: `GET /einvoice/authenticate?email=` + headers `username, password, ip_address, client_id, client_secret, gstin` (username /
  password = the **IRP API user** she creates on the e-invoice portal choosing the GSP "BVM IT Consulting", usually `API_...`); later calls
  headers `ip_address, client_id, client_secret, username, **auth-token**, gstin` - **we hold the auth-token** (response shape UNVERIFIED;
  NIC tokens ~6 h). Optional query `irp` = NIC1 / NIC2 - store the IRP per IRN and pass it on cancel / get.
- **e-Way Bill**: `GET /ewaybillapi/v1.03/authenticate?email=&username=&password=&irp=` + headers `ip_address, client_id, client_secret,
  gstin` - **the EWB password travels in the QUERY STRING** (scrub logs / proxies); later calls headers `ip_address, client_id,
  client_secret, username, gstin`, no token (session held by WhiteBooks).
- **Encryption**: every body is plain JSON in GSTN / NIC field names (no app_key / sek / hmac / REK) - the GSP encrypts. Exception: **DSC
  filing** `{"content":"<summary json>","pkcs7":"<signature>"}` - the client signs (not feasible server-side; EVC is our filing path).

## 4. Core endpoints
"Std GST" = headers `gst_username, state_cd, ip_address, txn, client_id, client_secret`; "Std EINV" = `ip_address, client_id,
client_secret, username, auth-token, gstin`; "Std EWB" = `ip_address, client_id, client_secret, username, gstin`; `email` everywhere.
| Family | Method + path | Params beyond std | Notes |
|---|---|---|---|
| Public | GET `/public/search` | q gstin; only client_id / secret headers | no OTP |
| Public | GET `/public/searchbypan` | q pan | |
| Public | GET `/public/rettrack` | q gstin, fy (YYYY-YY), opt type (R1) | no OTP - supplier filing check |
| Public | GET `/public/pref` | q gstin, fy; h state_cd, ip_address | QRMP preference |
| Auth | GET `/authentication/otprequest` / `authtoken` / `refreshtoken` / `logout` | see section 3 | |
| Auth | GET `/authentication/otpforevc` | q gstin, pan (authorised signatory), form_type | sends the EVC OTP |
| GSTR-1 | PUT `/gstr1/retsave` | h gstin, ret_period | full GSTR-1 JSON |
| GSTR-1 | POST `/gstr1/reset` | h gstin, ret_period | before filing only |
| GSTR-1 | GET `/gstr1/retsum` | q gstin, retperiod, opt smrytyp | summary + checksums for filing |
| GSTR-1 | GET `/gstr1/b2b`, b2ba, b2cl, b2cs, cdnr, cdnur, exp, nil, hsnsum, dociss, at, txp, ecom, supeco, einvoice | q gstin, retperiod, opt actionrequired, ctin, fromtime | |
| GSTR-1 | GET `/gstr1/validatehsnsum` | q gstin, retperiod | |
| Proceed | GET `/all/newproceedfile` | q gstin, retperiod, type GSTR1/5/6, opt isNil | |
| Status | GET `/gstr/retstatus` or `/all/newretstatus` | q gstin, returnperiod, refid (+ rettype) | poll after save / file |
| Track | GET `/gstr/rettrack` | q gstin, returnperiod, opt type | |
| GSTR-1 | POST `/gstr1/retfile` (DSC) / `/gstr1/retevcfile` (EVC) | q pan (+ evcotp); h gstin, ret_period | `{content}` / `{content, pkcs7}` |
| GSTR-1A | same set under `/gstr1a/*` + getdeclaration / confirmdeclaration / proceedfile | | |
| GSTR-3B | GET `/gstr3b/retsum`, `/gstr3b/autoliab` | q gstin, retperiod | auto-liability from 1 / 2B |
| GSTR-3B | PUT `/gstr3b/retsave`; POST `/gstr3b/validateautocalculatedata` | h gstin, ret_period | |
| GSTR-3B | POST `/gstr3b/cmpint`; GET `/gstr3b/syscalcintrst` | | interest |
| GSTR-3B | PUT `/gstr3b/retoffset` | h gstin, ret_period | `{pdcash[], pditc{}}` |
| GSTR-3B | PUT `/gstr3b/liabilitybreakup`; GET openingbal / closingbal / rcmopeningbal / rcmclosingbal; POST savercmopnbal | | |
| GSTR-3B | POST `/gstr3b/retfile` / `retevcfile` | q pan (+ evcotp) | |
| GSTR-2A | GET `/gstr2a/b2b`, b2ba, cdn, cdna, isd, impg, impgsez, tds, tcs, ecom, amdhist | q gstin, retperiod, opt ctin, fromtime | |
| GSTR-2B | GET `/gstr2b/all` | q gstin, rtnprd, opt filenum | large 2B paged |
| GSTR-2B | PUT `/gstr2b/gen2b` -> GET `/gstr2b/get2b` | get2b q gstin, int_tran_id | recompute after IMS |
| IMS | GET `/ims/invoices` | q gstin, section, opt status | |
| IMS | GET `/ims/invoicescount` | q gstin, goodsType | |
| IMS | PUT `/ims/save`, PUT `/ims/reset` | h gstin, ret_period | returns int_tran_id |
| IMS | GET `/ims/status` | q gstin, int_tran_id | |
| IMS | GET `/ims/supplierInvoices`, `/ims/rejectedInvoices`, `/ims/getfile` | | |
| Ledger | GET `/ledgers/cashdtl`, `/ledgers/itc`, `/ledgers/tax` | q gstin, frdt, todt | |
| Ledger | GET `/ledgers/bal` (q retperiod), `/ledgers/taxpayable` (+ rettype), itcblocktrandetls, revrclmdtl, negliabstmt, rcmldg | | |
| Ledger | POST `/ledgers/utlcsh`, `/ledgers/utlitc` | h gstin, ret_period | body undocumented |
| Payment | POST `/payment/generateChallan` | h gstin, ret_period | PMT-06 JSON - creates a CPIN, moves NO money |
| Payment | GET `/payment/chllnlst` (fromdate, todate), `/payment/chllnsum` (cpin) | | |
| Annual | `/gstr9/getautocal`, getdet, retsave, retfile / retevcfile, get8adetails, getHsndetails; `/gstr9c/*` | | |
| Large data | GET `/all/filedet` (token), `/all/largefile` (url, ek) | | token-based large responses |
| e-Invoice | GET `/einvoice/authenticate` | h username, password, gstin | |
| e-Invoice | POST `/einvoice/type/GENERATE/version/V1_03` | std EINV | INV-01 JSON v1.1 |
| e-Invoice | POST `/einvoice/type/CANCEL/version/V1_03` | opt irp | `{"Irn","CnlRsn","CnlRem"}`; **only within 24 h** |
| e-Invoice | GET `/einvoice/type/GETIRN/version/V1_03` | q param1=IRN, opt supplier_gstn, irp | **past 72 h only** |
| e-Invoice | GET `/einvoice/type/GETIRNBYDOCDETAILS/version/V1_03` | q param1=doc type; **h docnum, docdate (dd/MM/yyyy)** | recovery after a timeout |
| e-Invoice | GET GETREJECTEDIRNS (param1), GSTNDETAILS (param1=GSTIN), SYNC_GSTIN_FROMCP; POST GENERATE_EWAYBILL; GET GETEWAYBILLIRN | | |
| e-Invoice | GET `/einvoice/qrcode` | h sgstin, docno, docdate, totinvval, upiid, bankaccno, bankifsccode, accountholdername, tax amounts | B2C dynamic QR |
| e-Invoice (GST side) | GET `/gst/einvoice/irnlist`, irnjsons, irndtl, hsnsum, filedtl | GST session | IRNs as GSTN sees them |
| EWB | GET `/ewaybillapi/v1.03/authenticate` | q username, password, opt irp | |
| EWB | POST `.../ewayapi/genewaybill`, `vehewb`, `canewb`, `extendvalidity`, `updatetransporter`, `rejewb`, `gencewb`, `regentripsheet`, `initmulti`, `addmulti`, `updtmulti`, `clsewb` | std EWB | |
| EWB | GET `.../ewayapi/getewaybill` (ewbNo), `getewaybillgeneratedbyconsigner` (docType, docNo), getewaybillsbydate, ...fortransporter(bygstin / bystate), ...ofotherparty, ...rejectedbyothers, gettripsheet, gettransporterdetails, getgstindetails, gethsndetailsbyhsncode (hsncode), geterrorlist | | |
**Response envelope** (spec components): `{"status_cd":"1|0","status_desc":"...","error":{"message","error_cd","code","desc"},"header":{...},
"data":"..."}`. **No success body is documented per endpoint** - the shape of `data` (IRN, AckNo, SignedQRCode, EWB no, ARN, int_tran_id,
txn) is UNVERIFIED; expect GSTN / NIC native names inside `data` - confirm in the sandbox. Spec nit: `ctin` is the counterparty GSTIN.

**Bodies (VERIFIED from the specs; examples NOT arithmetically consistent - never test data):**
- e-invoice generate: NIC INV-01 v1.1 - `Version "1.1"`, `TranDtls {TaxSch GST, SupTyp B2B, RegRev, EcmGstin, IgstOnIntra}`, `DocDtls {Typ
  INV, No, Dt dd/MM/yyyy}`, `SellerDtls {Gstin, LglNm, TrdNm, Addr1, Addr2, Loc, Pin, Stcd, Ph, Em}`, `BuyerDtls {... Pos ...}`, optional
  DispDtls / ShipDtls, `ItemList[] {SlNo, IsServc, PrdDesc, HsnCd, Barcde, BchDtls, Qty, FreeQty, Unit, UnitPrice, TotAmt, Discount,
  PreTaxVal, AssAmt, GstRt, SgstAmt, IgstAmt, CgstAmt, CesRt, CesAmt, CesNonAdvlAmt, StateCesRt, StateCesAmt, StateCesNonAdvlAmt, OthChrg,
  TotItemVal, OrdLineRef, OrgCntry, PrdSlNo, AttribDtls[]}`, `ValDtls {AssVal, CgstVal, SgstVal, IgstVal, CesVal, StCesVal, Discount,
  OthChrg, RndOffAmt, TotInvVal, TotInvValFc}`, optional PayDtls, RefDtls, AddlDocDtls, ExpDtls, EwbDtls. Mandatory per FAQ: Version,
  TranDtls, DocDtls, SellerDtls, BuyerDtls (+ ItemList, ValDtls by NIC schema). Cancel `{"Irn","CnlRsn":"1","CnlRem"}`; EWB by IRN `{Irn,
  Distance, TransMode, TransId, TransName, TransDocDt, TransDocNo, VehNo, VehType, ExpShipDtls, DispDtls}`.
- GSTR-1 save: standard GSTN JSON - top-level `gstin, fp (MMYYYY), gt, cur_gt, b2b, b2ba, b2cl, b2cla, cdnr, cdnra, b2cs, b2csa, exp, expa,
  hsn, nil, txpd, txpda, at, ata, doc_issue, cdnur, cdnura`; invoice dates dd-MM-yyyy; b2b `[{ctin, inv:[{inum, idt, val, pos, rchrg, etin,
  inv_typ, diff_percent, itms:[{num, itm_det:{rt, txval, iamt | camt + samt, csamt}}]}]}]`; b2cs items `{sply_ty, rt, typ, pos, txval, iamt,
  csamt, etin, diff_percent}`; nil `inv[] {sply_ty, expt_amt, nil_amt, ngsup_amt}`; hsn `{data:[{num, hsn_sc, desc, uqc, qty, rt, txval,
  iamt, csamt}]}`; doc_issue `{doc_det:[{doc_num, docs:[{num, from, to, totnum, cancel, net_issue}]}]}`. **Hoola's `gstp.gstr1_json` and
  `appmaker/gstr1.py` already emit this shape (offline-tool JSON) - reuse.**
- GSTR-3B save: `{gstin, ret_period, sup_details {osup_det, osup_zero, osup_nil_exmp, isup_rev, osup_nongst}, inter_sup {comp_details,
  uin_details, unreg_details}, eco_dtls, itc_elg {itc_avl[{ty, iamt, camt, samt, csamt}], itc_rev, itc_net, itc_inelg}, inward_sup
  {isup_details[{ty, inter, intra}]}, intr_ltfee {intr_details}}`; offset `{pdcash[{liab_ldg_id, trans_typ, ipd, cpd, spd, cspd, i_intrpd,
  c_intrpd, s_intrpd, cs_intrpd, c_lfeepd, s_lfeepd}], pditc{liab_ldg_id, trans_typ, i_pdi, i_pdc, i_pds, c_pdi, c_pdc, s_pdi, s_pds,
  cs_pdcs}}` - `liab_ldg_id` / `trans_typ` come from the 3B summary `tx_pmt.tx_py[]` (30002 = other than reverse charge). Hoola's
  `gstp.prepare_gstr3b` computes these tables already.
- IMS save: `{rtin, reqtyp:"SAVE", invdata:{b2b | b2ba | b2bdn | b2bdna | b2bcn | b2bcna | ecom | ecoma:[{stin, rtnprd, srcform, inum, idt,
  inv_typ, pos, val, txval, iamt, camt, samt, cess, action A|R|P, prev_status}]}}` -> poll `/ims/status` -> `PUT /gstr2b/gen2b` -> `GET
  /gstr2b/get2b`.
- e-way bill generate: `{supplyType, subSupplyType, subSupplyDesc, docType, docNo, docDate, fromGstin, fromTrdName, fromAddr1/2, fromPlace,
  actFromStateCode, fromPincode, fromStateCode, toGstin, toTrdName, toAddr1/2, toPlace, toPincode, actToStateCode, toStateCode,
  transactionType, totalValue, cgstValue, sgstValue, igstValue, cessValue, cessNonAdvolValue, totInvValue, otherValue, transMode,
  transDistance, transporterName, transporterId, transDocNo, transDocDate, vehicleNo, vehicleType, itemList[{productName, productDesc,
  hsnCode, quantity, qtyUnit, taxableAmount, sgstRate, cgstRate, igstRate, cessRate, cessNonadvol}]}`; Part-B `{ewbNo, vehicleNo, fromPlace,
  fromState, reasonCode, reasonRem, transDocNo, transDocDate, transMode}`; cancel `{ewbNo, cancelRsnCode, cancelRmrk}`; extend + consolidated
  bodies in the spec. Hoola's `logistics/ewb.py bulk_json` already builds the NIC bulk shape - reuse its field mapping.
- Challan: `gstin, email_id, mobile_num, tp_name, address, payment_mod (OTC...), bank_cd, sub_pay_mod, ipAddr, {cgst|sgst|igst|cess}_{tax|
  int|fee|oth|pen}_amt, *_tot_amt, total_amt, chln_rsn (QRMP35...), chln_prd` - generating a CPIN moves no money.

## 5. Filing
GSTR-1 order: `retsave` (per section) -> poll `retstatus` with `refid` -> `retsum` (checksums) -> `newproceedfile type=GSTR1` -> file. Two
modes for every return (1 / 1A / 3B / 4 / 5 / 6 / 7 / 8 / 9 / 9A / 9C, CMP-08, ITC-03 / 04, 2X):
- **EVC (our path)**: `GET /authentication/otpforevc?gstin=&pan=<authorised signatory PAN>&form_type=R1|R3B...` -> OTP to the SIGNATORY ->
  `POST /.../retevcfile?pan=&evcotp=` body `{"content":"<retsum summary json string>"}`.
- DSC: `POST /.../retfile?pan=` `{content, pkcs7}` - needs her DSC token on her machine; out of scope for a cloud employee.
**Her own acts, by GSTN design**: the login OTP and the EVC OTP (or her DSC). Filing is irreversible; GSTR-1 / 1A `reset` only before
filing; 3B needs `retoffset` (tax / interest / fee settled) before filing.

## 6. Errors, limits, sessions, idempotency, sandbox
- Errors: **HTTP 200 + `status_cd:"0"`** + `status_desc` with a WhiteBooks code (`WB_ERR_9001` bad credentials / inactive); `WB_ERR_9000`
  (HTTP 500) unexpected / unknown route; e-invoice also `errorCode`; GSTN / NIC upstream codes expected in `error.error_cd` (UNVERIFIED).
  **Always branch on `status_cd`, never on the HTTP status.** The full WB_ERR catalogue is login-only.
- Rate limit sandbox 60/min; production by plan.
- Windows: **IRN cancel within 24 h; GETIRN + GETIRNBYDOCDETAILS past 72 h only.**
- **Idempotency**: IRN = hash(supplier GSTIN + doc type + doc number + FY); NIC **2150 Duplicate IRN**. Pattern: persist every generate
  response; on timeout or 2150 call GETIRNBYDOCDETAILS within 72 h and adopt the existing IRN; never fire the same request concurrently.
  EWB recovery `getewaybillgeneratedbyconsigner?docType=&docNo=`. GSTN saves overwrite per invoice key; poll retstatus by refid. No
  idempotency-key header. Cancelling an IRN with an active EWB fails (NIC **2174**) - cancel the EWB first.
- Sandbox: GST OTP **575757**; per-account sandbox GSTIN + usernames / passwords on the Hub Credentials page. Spec example GSTINs
  (29AAGCB1286Q000, 27AHQPA7588L1ZJ, 29AALCS0862D1ZJ) are examples only.

## 7. Pricing + terms
- Pricing page: software plans Rs 5,999 - 24,999 (quote by GSTINs, IRN / EWB volume, API vs dashboard); GST API page "Startup Rs 14,999 /
  month" (UNVERIFIED, conflicts); **Hub billing code: a yearly package per product (GST / e-Invoice / e-Way Bill) of N calls at Rs X per call,
  top-ups, overage from the next allocation, unused calls roll over; "production from Rs 15,000/yr"**. Per-call rate behind login - ask for
  the rate card; whether OTP / auth / status polls are billable is UNVERIFIED (a GSTR-1 filing is ~6-10 calls).
- **Terms s.3: "Do not resell or sublicense the services without WhiteBooks' explicit written agreement"** - the FAQ says CA firms / tax-tech
  may file for clients with multi-GSTIN delegated auth, but **Hoola serving many taxpayers needs a written ASP / reseller agreement**.
  Terms s.2: using filing services authorises WhiteBooks to add the user as a registered client on GSTN. ISO 27001:2022, TLS 1.2+, India
  residency (AWS Mumbai), AES-256 at rest, 7-year append-only audit logs, DPDP alignment; return-payload retention not stated.
- **Taxpayer enablement (GSTN rule)**: gst.gov.in -> My Profile -> **Manage API Access** -> Enable API Request = Yes -> pick the GSP / ASP + a
  duration **6 h - 30 days**; revocable; "Revoke Active Token" logs; until enabled the OTP request fails. For e-invoice / EWB she creates a
  separate **API user** on the e-invoice / EWB portal "through GSP" choosing BVM IT Consulting (username usually `API_...`).

## 8. Implementation advice
1. Code to the specs; branch on `status_cd`; `client_id` / `client_secret` server-side only (VPS .env), on every call.
2. Per-tenant session store: GST `gst_username, state_cd, txn, enabled_until`; e-invoice `auth-token` + the IRP per IRN; EWB username. IRP /
   EWB passwords collected through the app's sealed-credential door, never chat, never logged (the EWB password rides a query string).
3. The login OTP and the EVC OTP are her taps (the existing card + her-tap pattern); DSC not supported.
4. Persist every IRN / EWB response; recover duplicates via GETIRNBYDOCDETAILS / getewaybillgeneratedbyconsigner; track the 24 h cancel and
   72 h fetch windows.
5. Confirm with WhiteBooks before production: success response shapes (`txn`, `auth-token`, IRN / AckNo / SignedQRCode, `refid`,
   `int_tran_id`), session lifetimes, billable calls, whether x-api-key / OAuth exist on production, IP allow-listing, and **written
   permission to serve many taxpayers**.

## Sources
developer.whitebooks.in/assets/gst-api-Dg40VqhG.js (GST spec, 284 ops, OTP 575757) · .../e-invoice-api-qnrG8gEK.js (e-invoice spec, 24 h /
72 h, INV-01 v1.1) · .../e-way-bill-api-B3XJyHAb.js (EWB spec) · .../QuickstartGuide-T-ljo30V.js (base URLs, 60/min) ·
.../AuthenticationGuide-*.js, ErrorsGuide-*.js, ChangelogPage-*.js (prose claims, UNVERIFIED) · .../hooks-*.js, SubscriptionWizard-*.js,
SubscriptionsPage-*.js, CredentialsPage-*.js, LegalCompliancePage-*.js (sign-up, per-call packages, Rs 15,000/yr, sandbox creds, ISO /
residency) · apisandbox.whitebooks.in + api.whitebooks.in live probes (I-HUB, WB_ERR_9001 / 9000) · whitebooks.in/sitemap.xml ·
whitebooks.in/developer/gst-api/get-authentication-authtoken (+ otprequest, refreshtoken, public-search, put-ims-save) ·
whitebooks.in/developer/e-invoice-api/post-einvoice-type-generate-version-v1-03 · whitebooks.in/developer/e-way-bill-api/get-ewaybillapi-v1.03-authenticate
· whitebooks.in/apis/gst, /apis/e-invoice, /apis/security · whitebooks.in/about/pricing, /about/terms, /about/privacy-policy ·
registry.npmjs.org/@whitebooks%2fnode + pypi.org/pypi/whitebooks/json (SDKs absent) · simpleinvoicemanager.com (BVMIT as GSP, API_ user) ·
learn.quicko.com + cleartax.in/s/gst-api-access + tallysolutions.com (Manage API Access) · cleartax.in error 2150 + taxpro-gsp NoteToGSPsOnErrors.pdf (2150 / 2174).
