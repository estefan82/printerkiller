import PIL.Image
import PIL.ImageWin
import win32print
import win32ui


def print_image_directly(image_path, printer_name=None):
  if not printer_name:
    printer_name = win32print.GetDefaultPrinter()

  img = PIL.Image.open(image_path)

  hDC = win32ui.CreateDC()
  hDC.CreatePrinterDC(printer_name)

  printable_width = hDC.GetDeviceCaps(8)  # HORZRES
  printable_height = hDC.GetDeviceCaps(10)  # VERTRES

  hDC.StartDoc(image_path)
  hDC.StartPage()

  img_width, img_height = img.size
  ratio = min(printable_width / img_width, printable_height / img_height)

  new_width = int(img_width * ratio)
  new_height = int(img_height * ratio)

  x = (printable_width - new_width) // 2
  y = (printable_height - new_height) // 2

  dib = PIL.ImageWin.Dib(img)

  # CORRECCIÓN AQUÍ: Usar .GetSafeHdc() en lugar de .GetHandle()
  dib.draw(hDC.GetSafeHdc(), (x, y, x + new_width, y + new_height))

  hDC.EndPage()
  hDC.EndDoc()
  hDC.DeleteDC()

  print(
      f"Imagen '{image_path}' enviada con éxito a la impresora '{printer_name}'."
  )


if __name__ == "__main__":
  print_image_directly(r"C:\Users\estef\Desktop\ALE ESTA\ale.jpg")


