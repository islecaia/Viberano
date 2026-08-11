"""Utilidad de desarrollo: envía un correo de prueba con un PDF adjunto vía SMTP, para poder
probar el flujo de sincronización sin depender de facturas reales.

No forma parte de la aplicación (app/) ni de las tareas de la feature — es solo una herramienta
manual de testing. No guarda ni registra la contraseña en ningún sitio; se pide en el momento.

Uso:
    uv run python scripts/send_test_email.py
"""

import getpass
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from io import BytesIO

from pypdf import PdfWriter

SMTP_HOST = "mail.gmx.com"
SMTP_PORT = 587


def build_test_pdf() -> bytes:
    """Genera un PDF válido mínimo (página en blanco) usando pypdf, sin dependencias nuevas."""
    writer = PdfWriter()
    writer.add_blank_page(width=595, height=842)
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def build_message(email_address: str) -> MIMEMultipart:
    msg = MIMEMultipart()
    msg["From"] = email_address
    msg["To"] = email_address
    msg["Subject"] = "Factura de prueba - Proveedor Test SL"
    msg.attach(
        MIMEText(
            "Correo de prueba generado para probar la ingesta de facturas.\n"
            "Adjunto: factura-prueba.pdf (documento en blanco, solo para probar el flujo "
            "de conexión/sincronización, no el contenido de la factura).",
            "plain",
        )
    )

    attachment = MIMEApplication(build_test_pdf(), _subtype="pdf")
    attachment.add_header("Content-Disposition", "attachment", filename="factura-prueba.pdf")
    msg.attach(attachment)
    return msg


def main() -> None:
    email_address = input("Dirección de correo GMX (remitente y destinatario): ").strip()
    password = getpass.getpass("Contraseña: ")

    msg = build_message(email_address)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(email_address, password)
        server.send_message(msg)

    print(f"Correo de prueba enviado a {email_address}.")


if __name__ == "__main__":
    main()
