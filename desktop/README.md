# Santosh Desktop

> 🔒 **FROZEN BY OWNER (25 Oct 2026)** — Mera PC / Santosh Desktop is feature-complete (desktop 1.3.1).
> Do not change anything in this folder until the developer explicitly asks. Full list of frozen paths: top of `/CLAUDE.md`.

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

## Build SantoshDesktop.exe (Windows, 64-bit Python 3.12)
    cd desktop
    pip install -r requirements.txt pyinstaller
    pyinstaller santosh_desktop.spec

Output: `dist\SantoshDesktop.exe` (onefile, no console). Always build with the spec — it excludes
`PIL._avif` (an unused ~1.5 MB AVIF codec that makes first-launch extraction slow and fragile)
and keeps UPX off (UPX-packed exes trip antivirus false positives). Publish the exe size and
`certutil -hashfile dist\SantoshDesktop.exe SHA256` output with the release so users can verify
a complete download.

## "Failed to extract PIL_.avif... decompression resulted in return code -1!"
This popup comes from the exe itself at launch: the onefile bootloader unpacks its payload into
`%TEMP%\_MEIxxxx` and one file failed to come out intact. In order of likelihood:

1. **Incomplete download.** Re-download `SantoshDesktop.exe` from the release and compare the file
   size (right-click > Properties > Size) with the size published on the release page. A download
   cut mid-way is the most common cause.
2. **Antivirus interference.** Defender or a third-party AV can lock the `.pyd` while it is being
   written to `%TEMP%`. Add an exclusion for the folder that holds the exe (e.g. Downloads), clear
   leftover `%TEMP%\_MEI*` folders (Win+R > `%TEMP%`), and launch again.
3. **Disk space / permissions.** Make sure the C: drive has a few hundred MB free, and try
   right-click > Run as administrator once.

Exes built with `santosh_desktop.spec` (desktop 1.3.1+) never contain the AVIF module, so this
specific failure cannot happen; the steps above still apply to any "Failed to extract" popup.
