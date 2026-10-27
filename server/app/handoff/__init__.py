"""v0.116 Hand-offs to India's official consent rails (Hoola Deals phase 6).

Hoola is not a regulated party on these rails, so it never becomes one:
- aa.py          Account Aggregator (RBI NBFC-AA). Hoola is NOT an FIU: it reads a consent request with her, flags what is
                 more than the purpose needs, and hands her to her own AA app to approve / reject / revoke. No financial
                 data ever comes to Hoola through AA.
- abdm.py        ABDM (NHA). Hoola is NOT a consent manager, HIP or HIU: it explains a health-record consent request, flags
                 broad ones, reminds her to revoke, and she decides in her PHR app (ABHA app). No health record is read.
- digilocker.py  DigiLocker requester (Meri Pehchaan OAuth 2.0 + PKCE): with the server's own requester credentials she
                 signs in on DigiLocker's page (OTP there, never in Hoola) and Hoola pulls HER issued documents into her
                 files. ID documents (Aadhaar, PAN, DL, RC, voter, passport, ration) never go to another person's avatar.
- ondc.py        Optional ONDC listing: readiness check + catalogue export for the seller app she chooses (a registered
                 seller network participant). Hoola never connects to the ONDC network itself.
"""
