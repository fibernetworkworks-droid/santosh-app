# Santosh Desktop

Connects an office or home PC to Santosh on the phone. The PC dials out to the Santosh server (no port forwarding),
so it works behind any broadband router.

What Santosh can do on this PC (only inside the folders you share):
- find files by name or content (party name, invoice no, GST, bank statement) and send them to the phone at full quality
- read PDF / Word / Excel / text files to answer questions
- save files sent from the phone into `Documents\Santosh Inbox`
- print a file (only after you tap Approve on the phone)
- TallyPrime: receivables, payables, ledgers, sales/purchase/receipt/payment vouchers, day book, stock (read-only);
  a simple voucher entry only after you tap Approve on the phone

Safety: a 6-digit code from the phone pairs the PC; the PC keeps its own token (encrypted with Windows DPAPI).
Removing the PC in the app disconnects it at once. "Rokiye" (pause) on the PC stops everything. Every action is shown
in the window and in the app's activity list.

## TallyPrime
In TallyPrime: Help > Settings > Connectivity > Client/Server configuration: "TallyPrime acts as" = Server, port 9000.

## Run from source
    pip install -r requirements.txt
    python -m santosh_desktop                     # window
    python -m santosh_desktop --headless --code 123456 --folder "D:\Accounts"

The server is fixed: https://hoola.ainewtika.com (a test machine can set HOOLA_SERVER or pass --server).
