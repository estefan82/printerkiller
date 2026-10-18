import os
import pymupdf
from nicegui import ui
import PIL.Image
import PIL.ImageWin
import win32print
import win32ui
from docx2pdf import convert

# Directorio de almacenamiento temporal
UPLOAD_DIR = os.path.join(os.path.expanduser("~"), "print_uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf", ".docx"}

# Variables globales para la UI
log_box = None
file_list_container = None
uploaded_files_history = []


def log_message(msg):
  """Envía un mensaje tanto a la consola como a la caja de logs de la UI"""
  print(msg)
  if log_box:
    log_box.push(msg)

def update_file_list():
  """Actualiza visualmente la lista de archivos recientes en la interfaz"""
  if file_list_container:
    file_list_container.clear()
    with file_list_container:
      if not uploaded_files_history:
        ui.label("No hay archivos impresos aún.").classes(
            "text-gray-400 text-sm italic"
        )
      for filename in reversed(uploaded_files_history[-10:]):
        with ui.row().classes(
            "w-full justify-between items-center bg-gray-50 px-3 py-2 rounded"
            " border border-gray-100"
        ):
          ui.label(filename).classes("text-sm truncate max-w-[400px]")
          ui.badge("Impreso", color="green").props("outline")

def clear_history():
  """Limpia el historial de archivos recientes"""
  uploaded_files_history.clear()
  update_file_list()
  log_message("[INFO] Historial de archivos limpiado.")

def print_page_image(pil_img, printer_name):
  hDC = win32ui.CreateDC() # noqa
  hDC.CreatePrinterDC(printer_name)

  printable_width = hDC.GetDeviceCaps(8)  # HORZRES
  printable_height = hDC.GetDeviceCaps(10)  # VERTRES

  hDC.StartDoc("PrintJob")
  hDC.StartPage()

  img_width, img_height = pil_img.size
  ratio = min(printable_width / img_width, printable_height / img_height)

  new_width = int(img_width * ratio)
  new_height = int(img_height * ratio)

  x = (printable_width - new_width) // 2
  y = (printable_height - new_height) // 2

  dib = PIL.ImageWin.Dib(pil_img)
  dib.draw(hDC.GetSafeHdc(), (x, y, x + new_width, y + new_height))

  hDC.EndPage()
  hDC.EndDoc()
  hDC.DeleteDC()

def universal_print(file_path, printer_name=None):
  if not printer_name:
    printer_name = win32print.GetDefaultPrinter()

  ext = os.path.splitext(file_path)[1].lower()
  pdf_to_process = file_path
  temp_pdf_created = False

  try:
    if ext == ".docx":
      log_message("[PROCESO] Convirtiendo DOCX a PDF temporal...")
      pdf_to_process = os.path.splitext(file_path)[0] + "_temp.pdf"
      convert(file_path, pdf_to_process)
      temp_pdf_created = True
      ext = ".pdf"

    if ext in [".jpg", ".jpeg", ".png"]:
      log_message(
          f"[IMPRESIÓN] Procesando imagen para '{printer_name}'..."
      )
      img = PIL.Image.open(file_path)
      print_page_image(img, printer_name)

    elif ext == ".pdf":
      log_message(f"[IMPRESIÓN] Rasterizando PDF para '{printer_name}'...")
      doc = pymupdf.open(pdf_to_process)
      for page_num in range(len(doc)):
        page = doc[page_num]
        pix = page.get_pixmap(dpi=300)
        img = PIL.Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        print_page_image(img, printer_name)
      doc.close()
    else:
      raise ValueError(f"Formato no soportado: {ext}")

    log_message(f"[ÉXITO] Trabajo enviado correctamente a '{printer_name}'.")

  finally:
    if temp_pdf_created and os.path.exists(pdf_to_process):
      try:
        os.remove(pdf_to_process)
      except Exception:
        pass

async def handle_upload(e):
  filename = e.file.name
  ext = os.path.splitext(filename)[1].lower()

  if ext not in ALLOWED_EXTENSIONS:
    ui.notify(
        f"Formato no permitido ({ext}). Usa JPG, PNG, PDF o DOCX.",
        type="warning",
        position="top",
    )
    log_message(f"[AVISO] Intento de subida con formato no válido: {filename}")
    return

  file_path = os.path.join(UPLOAD_DIR, filename)
  content = await e.file.read()
  with open(file_path, "wb") as f:
    f.write(content)

  log_message(f"[RECIBIDO] Archivo '{filename}' guardado en servidor.")
  ui.notify(f"Archivo '{filename}' recibido. Imprimiendo...", type="info")

  try:
    universal_print(file_path)
    ui.notify(
        f"¡Impresión completada para '{filename}'!",
        type="positive",
        position="top",
    )
    uploaded_files_history.append(filename)
    update_file_list()
  except Exception as ex:
    ui.notify(f"Error al imprimir: {str(ex)}", type="negative", position="top")
    log_message(f"[ERROR] Fallo al imprimir {filename}: {ex}")

@ui.page("/")
def main_page():
  global log_box, file_list_container

  # Cabecera superior simple y limpia
  with ui.header().classes(
      "items-center justify-between bg-primary text-white px-6 py-4 shadow-md"
  ):
    ui.label("🖨️ Print Server V1.0").classes("text-xl font-bold tracking-wide")

  # Contenedor único centralizado (1 sola columna)
  with ui.column().classes("w-full max-w-4xl mx-auto p-6 gap-6 items-stretch"):

    # 1. Zona Gigante de Drag & Drop
    with ui.card().classes("p-8 shadow-lg rounded-2xl flex flex-col gap-4"):
      ui.label("Panel de Impresión Remota").classes(
          "text-2xl font-bold text-gray-800"
      )
      ui.label(
          "Sube tus archivos JPG, PNG, PDF o DOCX para imprimir"
      ).classes("text-gray-500 text-sm")

      # Componente upload más amplio y destacado
      ui.upload(
          on_upload=handle_upload,
          auto_upload=True,
          max_file_size=20 * 1024 * 1024,
      ).classes("w-full h-48 border-2 border-dashed border-primary/40 rounded-xl flex items-center justify-center p-4 bg-blue-50/20").props(
          'accept=".jpg, .jpeg, .png, .pdf, .docx" label="Arrastra aquí tus'
          ' archivos o haz clic para buscar"'
      )

    # 2. Historial de Archivos
    with ui.card().classes("p-6 shadow-md rounded-2xl flex flex-col gap-3"):
      with ui.row().classes("justify-between items-center w-full"):
        ui.label("Archivos Recientes").classes(
            "font-semibold text-lg text-gray-700"
        )
        ui.button(
            "Limpiar Historial", icon="delete", on_click=clear_history
        ).props("flat color=negative size=sm")

      file_list_container = ui.column().classes(
          "w-full gap-2 max-h-[200px] overflow-y-auto pr-1"
      )
      update_file_list()

if __name__ == "__main__":
  try:
    ui.run(port=8082, host="0.0.0.0", title="Print Server V1.0", reload=False)
  except (KeyboardInterrupt, SystemExit):
    print("\n[INFO] Servidor detenido correctamente.")
  except Exception as e:
    print(f"\n[ERROR CRÍTICO] {e}")