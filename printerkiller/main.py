import os
from nicegui import ui

UPLOAD_DIR = os.path.join(os.path.expanduser("~"), "print_uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".pdf", ".docx"}


def print_file(file_path, filename):
  """Envía el archivo a la impresora predeterminada en Windows usando el comando

  nativo del sistema operativo.
  """
  try:
    # 'print' le indica a Windows que mande el archivo a la impresora predeterminada
    os.startfile(file_path, "print")
    ui.notify(
        f"¡Trabajo de impresión enviado para '{filename}'!",
        type="positive",
        position="top",
    )
  except Exception as e:
    ui.notify(
        f"Error al imprimir {filename}: {str(e)}",
        type="negative",
        position="top",
    )
    print(f"Error de impresión: {e}")


async def handle_upload(e):
  filename = e.file.name
  ext = os.path.splitext(filename)[1].lower()

  if ext not in ALLOWED_EXTENSIONS:
    ui.notify(
        f"Formato no permitido ({ext}). Usa JPG, PDF o DOCX.",
        type="warning",
        position="top",
    )
    return

  file_path = os.path.join(UPLOAD_DIR, filename)

  # Al ser asíncrono, necesitamos 'await' para leer los bytes del archivo
  content = await e.file.read()

  with open(file_path, "wb") as f:
    f.write(content)

  ui.notify(f"Archivo '{filename}' recibido. Imprimiendo...", type="info")
  print_file(file_path, filename)

@ui.page("/")
def main_page():
  with ui.card().classes(
      "absolute-center items-center p-8 shadow-lg rounded-xl w-[500px]"
  ):
    ui.label("Servidor de Impresión Remota").classes("text-2xl font-bold mb-2")
    ui.label(
        "Sube un archivo JPG, PDF o DOCX para enviarlo a la impresora del"
        " servidor."
    ).classes("text-gray-500 mb-6 text-center")

    ui.upload(
        on_upload=handle_upload,
        auto_upload=True,
        max_file_size=20 * 1024 * 1024,
    ).classes("max-w-full").props(
        'accept=".jpg, .jpeg, .pdf, .docx" label="Haz clic o arrastra tu'
        ' archivo aquí"'
    )


ui.run(port=8080, host="0.0.0.0", title="Print Server", reload=False)