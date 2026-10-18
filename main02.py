import os
import fitz  # PyMuPDF
from nicegui import ui
import PIL.Image
import PIL.ImageWin
import win32print
import win32ui

# Directorio donde se guardarán temporalmente los archivos subidos
UPLOAD_DIR = os.path.join(os.path.expanduser("~"), "print_uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf"}


def print_page_image(pil_img, printer_name):
  """Función auxiliar que toma una imagen PIL y la dibuja directamente

  en el contexto gráfico (GDI) de la impresora predeterminada de Windows.
  """
  hDC = win32ui.CreateDC()
  hDC.CreatePrinterDC(printer_name)

  # Obtener el área imprimible en píxeles
  printable_width = hDC.GetDeviceCaps(8)  # HORZRES
  printable_height = hDC.GetDeviceCaps(10)  # VERTRES

  hDC.StartDoc("PrintJob")
  hDC.StartPage()

  # Escalar manteniendo la proporción (Aspect Ratio)
  img_width, img_height = pil_img.size
  ratio = min(printable_width / img_width, printable_height / img_height)

  new_width = int(img_width * ratio)
  new_height = int(img_height * ratio)

  # Centrar en la página
  x = (printable_width - new_width) // 2
  y = (printable_height - new_height) // 2

  dib = PIL.ImageWin.Dib(pil_img)
  dib.draw(hDC.GetSafeHdc(), (x, y, x + new_width, y + new_height))

  hDC.EndPage()
  hDC.EndDoc()
  hDC.DeleteDC()


def universal_print(file_path, printer_name=None):
  """Motor universal: detecta el tipo de archivo, lo rasteriza a imagen

  si es necesario y lo envía a la impresora de forma silenciosa.
  """
  if not printer_name:
    printer_name = win32print.GetDefaultPrinter()

  ext = os.path.splitext(file_path)[1].lower()

  if ext in [".jpg", ".jpeg", ".png"]:
    # Si es imagen, se procesa directamente con Pillow
    img = PIL.Image.open(file_path)
    print_page_image(img, printer_name)

  elif ext == ".pdf":
    # Si es PDF, cada página se convierte a imagen a alta calidad (300 DPI)
    doc = fitz.open(file_path)
    for page_num in range(len(doc)):
      page = doc[page_num]
      pix = page.get_pixmap(dpi=300)
      img = PIL.Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
      print_page_image(img, printer_name)
    doc.close()
  else:
    raise ValueError(f"Formato no soportado: {ext}")


async def handle_upload(e):
  filename = e.file.name
  ext = os.path.splitext(filename)[1].lower()

  if ext not in ALLOWED_EXTENSIONS:
    ui.notify(
        f"Formato no permitido ({ext}). Usa JPG, PNG o PDF.",
        type="warning",
        position="top",
    )
    return

  file_path = os.path.join(UPLOAD_DIR, filename)

  # Leer y guardar el archivo recibido desde la web
  content = await e.file.read()
  with open(file_path, "wb") as f:
    f.write(content)

  ui.notify(f"Archivo '{filename}' recibido. Imprimiendo...", type="info")

  try:
    # Llamada al sistema de impresión universal
    universal_print(file_path)
    ui.notify(
        f"¡Impresión completada con éxito para '{filename}'!",
        type="positive",
        position="top",
    )
  except Exception as ex:
    ui.notify(f"Error al imprimir: {str(ex)}", type="negative", position="top")
    print(f"Error de impresión detallado: {ex}")


@ui.page("/")
def main_page():
  with ui.card().classes(
      "absolute-center items-center p-8 shadow-lg rounded-xl w-[500px]"
  ):
    ui.label("Servidor de Impresión Universal").classes(
        "text-2xl font-bold mb-2"
    )
    ui.label(
        "Sube un archivo JPG, PNG o PDF para enviarlo a la impresora"
        " silenciosamente."
    ).classes("text-gray-500 mb-6 text-center")

    ui.upload(
        on_upload=handle_upload,
        auto_upload=True,
        max_file_size=20 * 1024 * 1024,  # Límite de 20 MB
    ).classes("max-w-full").props(
        'accept=".jpg, .jpeg, .png, .pdf" label="Haz clic o arrastra tu'
        ' archivo aquí"'
    )


if __name__ == "__main__":
  ui.run(port=8080, host="0.0.0.0", title="Print Server", reload=False)