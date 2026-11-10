"""v0.587 EXCEL BINA NAAM: the long card read a delivered workbook by PATH, and a delivered file is stored by its
id with no extension - openpyxl refused it unread (InvalidFileException), so her rent_xlsx job scored 'failed'
on a good file. The card now reads the bytes; a truly broken file still fails."""
from openpyxl import Workbook


def test_xlsx_without_extension_is_read(tmp_path):
    from app.quality.longcard import read_file
    wb = Workbook()
    ws = wb.active
    for row in (["city", "rent"], ["Mumbai", "45000"], ["Pune", "25000"], ["Bengaluru", "32000"]):
        ws.append(row)
    p = tmp_path / "file_abc123"           # how mailbox.store_bytes names it
    wb.save(p)
    info = read_file(str(p), "xlsx")
    assert info["ok"] and info["rows"] == 3 and "Bengaluru" in info["text"]


def test_broken_xlsx_still_fails(tmp_path):
    from app.quality.longcard import read_file
    p = tmp_path / "file_bad"
    p.write_text("city,rent\nMumbai,45000\n")
    info = read_file(str(p), "xlsx")
    assert not info["ok"] and "unreadable" in info["why"]


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.737.0"
