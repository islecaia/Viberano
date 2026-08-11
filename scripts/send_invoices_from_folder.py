"""Utilidad de desarrollo: envía cada PDF de una carpeta como un correo independiente, para
poblar un buzón de pruebas con varias facturas candidatas de una sola vez.

No forma parte de la aplicación (app/) ni de las tareas de la feature — es solo una herramienta
manual de testing. No guarda ni registra la contraseña en ningún sitio; se pide en el momento.

Uso:
    uv run python scripts/send_invoices_from_folder.py
    uv run python scripts/send_invoices_from_folder.py --folder otra_carpeta
"""

import argparse
import getpass
import smtplib
import time
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

SMTP_HOST = "mail.gmx.com"
SMTP_PORT = 587
DEFAULT_FOLDER = "facturas"
DELAY_BETWEEN_ENVIOS_SEGUNDOS = 1


def build_message(email_address: str, pdf_path: Path) -> MIMEMultipart:
    msg = MIMEMultipart()
    msg["From"] = email_address
    msg["To"] = email_address
    msg["Subject"] = f"Factura - {pdf_path.stem}"
    msg.attach(
        MIMEText(
            f"Correo de prueba generado a partir de {pdf_path.name} "
            "para probar la ingesta de facturas.",
            "plain",
        )
    )

    attachment = MIMEApplication(pdf_path.read_bytes(), _subtype="pdf")
    attachment.add_header("Content-Disposition", "attachment", filename=pdf_path.name)
    msg.attach(attachment)
    return msg


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--folder",
        default=DEFAULT_FOLDER,
        help=f"Carpeta con los PDF a enviar (por defecto: {DEFAULT_FOLDER}/)",
    )
    args = parser.parse_args()

    folder = Path(args.folder)
    if not folder.exists():
        folder.mkdir(parents=True)
        print(f"La carpeta {folder}/ no existía; la he creado.")
        print("Mete tus PDF ahí y vuelve a ejecutar el script.")
        return

    pdf_files = sorted(folder.glob("*.pdf"))
    if not pdf_files:
        print(f"No he encontrado ningún .pdf en {folder}/.")
        return

    print(f"Encontrados {len(pdf_files)} PDF en {folder}/:")
    for pdf_path in pdf_files:
        print(f"  - {pdf_path.name}")

    email_address = input("Dirección de correo GMX (remitente y destinatario): ").strip()
    password = getpass.getpass("Contraseña: ")

    enviados, fallidos = 0, []
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(email_address, password)
        for pdf_path in pdf_files:
            try:
                server.send_message(build_message(email_address, pdf_path))
                print(f"Enviado: {pdf_path.name}")
                enviados += 1
            except smtplib.SMTPException as exc:
                print(f"Fallo al enviar {pdf_path.name}: {exc}")
                fallidos.append(pdf_path.name)
            time.sleep(DELAY_BETWEEN_ENVIOS_SEGUNDOS)

    print(f"\n{enviados}/{len(pdf_files)} correos enviados a {email_address}.")
    if fallidos:
        print(f"Fallaron: {', '.join(fallidos)}")


if __name__ == "__main__":
    main()
