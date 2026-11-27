"""Off-server copy of the newest database backup.

The VPS keeps 30 days of backups on its own disk; if the server is lost, those go with it. This sends the newest one
off the server every day, encrypted so a mailbox or cloud folder never holds readable customer data:

    python -m app.tools.offsite_backup send            # email the newest backup (run by deploy/vps/backup.sh)
    python -m app.tools.offsite_backup decrypt IN OUT  # turn a .enc file back into the .sql.gz to restore

Needs BACKUP_PASSPHRASE in .env (keep a copy of it somewhere other than the server: without it a backup can't be
opened). Sent to BACKUP_EMAIL_TO, else the admin's notify address. Files over BACKUP_EMAIL_MAX_MB are not emailed
(the email says so); use BACKUP_RCLONE_REMOTE in deploy/vps/.env for those.
"""

import base64
import hashlib
import logging
import sys
from pathlib import Path

from cryptography.fernet import Fernet

from app.config import settings

logger = logging.getLogger("app.offsite_backup")
FOLDER = Path("/backups")


def _key(passphrase: str) -> Fernet:
    digest = hashlib.pbkdf2_hmac("sha256", passphrase.encode(), b"virundhu-offsite-backup-v1", 390_000)
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_file(src: Path, passphrase: str) -> bytes:
    return _key(passphrase).encrypt(src.read_bytes())


def decrypt_bytes(blob: bytes, passphrase: str) -> bytes:
    return _key(passphrase).decrypt(blob)


def newest(folder: Path = FOLDER) -> Path | None:
    files = sorted(folder.glob("virundhu-*.sql.gz"))
    return files[-1] if files else None


def send(folder: Path = FOLDER) -> str:
    from app.services.emailer import send_email

    if not settings.BACKUP_PASSPHRASE:
        return "skipped: BACKUP_PASSPHRASE is not set"
    src = newest(folder)
    if src is None:
        return "skipped: no backup file yet"
    to = [settings.BACKUP_EMAIL_TO or settings.notify_email]
    size_mb = src.stat().st_size / 1_000_000
    if size_mb > settings.BACKUP_EMAIL_MAX_MB:
        send_email(
            to,
            f"Virundhu backup too big to email ({size_mb:.0f} MB)",
            f"Today's backup {src.name} is {size_mb:.0f} MB, over the email limit. "
            "Set BACKUP_RCLONE_REMOTE in deploy/vps/.env to copy backups to Google Drive or S3 instead.",
        )
        return "too big: notice sent"
    blob = encrypt_file(src, settings.BACKUP_PASSPHRASE)
    ok = send_email(
        to,
        f"Virundhu backup {src.name.removeprefix('virundhu-').removesuffix('.sql.gz')}",
        "Today's encrypted database backup is attached. Keep these emails: they are your copy if the server is lost."
        "\n\nTo restore: python -m app.tools.offsite_backup decrypt <file>.enc backup.sql.gz"
        " (asks for BACKUP_PASSPHRASE),\n"
        "then bash tools/backup/restore.sh backup.sql.gz (see CLAUDE.md, Backups).",
        attachments=[(src.name + ".enc", blob, "application/octet-stream")],
    )
    return f"sent {src.name} ({size_mb:.1f} MB)" if ok else "email failed"


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    if len(sys.argv) >= 2 and sys.argv[1] == "send":
        logger.info("Off-server backup: %s", send())
    elif len(sys.argv) == 4 and sys.argv[1] == "decrypt":
        import getpass

        pw = settings.BACKUP_PASSPHRASE or getpass.getpass("BACKUP_PASSPHRASE: ")
        Path(sys.argv[3]).write_bytes(decrypt_bytes(Path(sys.argv[2]).read_bytes(), pw))
        logger.info("Decrypted to %s", sys.argv[3])
    else:
        logger.info(__doc__)


if __name__ == "__main__":
    main()
