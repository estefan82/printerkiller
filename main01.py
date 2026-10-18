import os
import pymupdf
from nicegui import ui
import PIL.Image
import PIL.ImageWin
import win32print
import win32ui
from docx2pdf import convert

# Directorio donde se guardarán temporalmente los archivos subidos
UPLOAD_DIR = os.path.join(os.path.expanduser("~"), "print_uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf", ".docx"}

def print_page_image(pil_img, printer_name):
  """Dibuja una imagen directamente en el contexto gráfico (GDI)

  de la impresora seleccionada en Windows.
  """
  hDC = win32ui.CreateDC() # noqa
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
  """Motor universal: maneja JPG, PNG, PDF y DOCX, los rasteriza a imagen

  y los envía a la impresora de forma silenciosa.
  """
  if not printer_name:
    printer_name = win32print.GetDefaultPrinter()

  ext = os.path.splitext(file_path)[1].lower()
  pdf_to_process = file_path
  temp_pdf_created = False

  try:
    # 1. Si es Word (.docx), se convierte primero a PDF temporal
    if ext == ".docx":
      pdf_to_process = os.path.splitext(file_path)[0] + "_temp.pdf"
      convert(file_path, pdf_to_process)
      temp_pdf_created = True
      ext = ".pdf"

    # 2. Si es imagen, imprimir directamente con Pillow
    if ext in [".jpg", ".jpeg", ".png"]:
      img = PIL.Image.open(file_path)
      print_page_image(img, printer_name)

    # 3. Si es PDF (o el PDF derivado del DOCX), rasterizar a 300 DPI
    elif ext == ".pdf":
      doc = pymupdf.open(pdf_to_process)
      for page_num in range(len(doc)):
        page = doc[page_num]
        pix = page.get_pixmap(dpi=300)
        img = PIL.Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        print_page_image(img, printer_name)
      doc.close()

    else:
      raise ValueError(f"Formato no soportado: {ext}")

  finally:
    # Limpieza del PDF temporal si se generó desde un DOCX
    if temp_pdf_created and os.path.exists(pdf_to_process):
      try:
        os.remove(pdf_to_process)
      except Exception as clean_err:
        print(f"Error limpiando PDF temporal: {clean_err}")

async def handle_upload(e):
  filename = e.file.name
  ext = os.path.splitext(filename)[1].lower()

  if ext not in ALLOWED_EXTENSIONS:
    ui.notify(
        f"Formato no permitido ({ext}). Usa JPG, PNG, PDF o DOCX.",
        type="warning",
        position="top",
    )
    return

  file_path = os.path.join(UPLOAD_DIR, filename)

  # Leer y guardar el archivo recibido desde la web
  content = await e.file.read()
  with open(file_path, "wb") as f:
    f.write(content)

  ui.notify(f"Archivo '{filename}' recibido. Procesando...", type="info")

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
        "Sube un archivo JPG, PNG, PDF o DOCX para enviarlo a la impresora"
        " silenciosamente."
    ).classes("text-gray-500 mb-6 text-center")

    ui.upload(
        on_upload=handle_upload,
        auto_upload=True,
        max_file_size=20 * 1024 * 1024,  # Límite de 20 MB
    ).classes("max-w-full").props(
        'accept=".jpg, .jpeg, .png, .pdf, .docx" label="Haz clic o arrastra tu'
        ' archivo aquí"'
    )

if __name__ == "__main__":
  try:
    ui.run(port=8080, host="0.0.0.0", title="Print Server", reload=False)
  except (KeyboardInterrupt, SystemExit):
    print("\n[INFO] Servidor de impresión detenido correctamente por el usuario.")
  except Exception as e:
    print(f"\n[ERROR CRÍTICO] El servidor se ha detenido inesperadamente: {e}")