import os
import pymupdf
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
import uvicorn
import PIL.Image
import PIL.ImageWin
import win32print
import win32ui
from docx2pdf import convert

app = FastAPI(title="Print Server HTML")

UPLOAD_DIR = os.path.join(os.path.expanduser("~"), "print_uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf", ".docx"}
recent_files = []


# --- MOTOR DE IMPRESIÓN ---
def print_page_image(pil_img, printer_name):
    hDC = win32ui.CreateDC()
    hDC.CreatePrinterDC(printer_name)

    printable_width = hDC.GetDeviceCaps(8)
    printable_height = hDC.GetDeviceCaps(10)

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
            pdf_to_process = os.path.splitext(file_path)[0] + "_temp.pdf"
            convert(file_path, pdf_to_process)
            temp_pdf_created = True
            ext = ".pdf"

        if ext in [".jpg", ".jpeg", ".png"]:
            img = PIL.Image.open(file_path)
            print_page_image(img, printer_name)
        elif ext == ".pdf":
            doc = pymupdf.open(pdf_to_process)
            for page_num in range(len(doc)):
                page = doc[page_num]
                pix = page.get_pixmap(dpi=300)
                img = PIL.Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                print_page_image(img, printer_name)
            doc.close()
    finally:
        if temp_pdf_created and os.path.exists(pdf_to_process):
            try:
                os.remove(pdf_to_process)
            except:
                pass


# --- ENDPOINTS WEB ---
@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Print Server V1.0</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gray-100 min-h-screen flex flex-col items-center justify-center p-4">

        <div class="w-full max-w-xl bg-white shadow-xl rounded-2xl p-8 flex flex-col gap-6">
            <div class="text-center">
                <h1 class="text-2xl font-bold text-gray-800">🖨️ Print Server V1.0</h1>
                <p class="text-gray-500 text-sm mt-1">Arrastra tus archivos para imprimirlos de forma silenciosa</p>
            </div>

            <!-- Zona de Drag & Drop Gigante -->
            <label id="drop-zone" class="border-3 border-dashed border-blue-400 bg-blue-50/50 hover:bg-blue-50 transition rounded-2xl h-56 flex flex-col items-center justify-center cursor-pointer p-6 text-center">
                <svg class="w-12 h-12 text-blue-500 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"></path>
                </svg>
                <span class="text-gray-700 font-medium">Haz clic o arrastra tus archivos aquí</span>
                <span class="text-gray-400 text-xs mt-1">JPG, PNG, PDF, DOCX (Máx. 20MB)</span>
                <input type="file" id="file-input" class="hidden" accept=".jpg,.jpeg,.png,.pdf,.docx" onchange="uploadFile(this)">
            </label>

            <!-- Estado / Mensaje -->
            <div id="status-box" class="hidden p-4 rounded-xl text-sm font-medium text-center"></div>

            <!-- Historial Reciente -->
            <div class="flex flex-col gap-2">
                <h2 class="font-semibold text-gray-700 text-sm">Archivos Impresos Recientemente</h2>
                <div id="history-list" class="flex flex-col gap-2 max-h-40 overflow-y-auto">
                    <span class="text-gray-400 text-xs italic">No hay archivos impresos aún.</span>
                </div>
            </div>
        </div>

        <script>
            async function uploadFile(input) {
                if (input.files.length === 0) return;
                const file = input.files[0];
                const formData = new FormData();
                formData.append("file", file);

                const statusBox = document.getElementById("status-box");
                statusBox.className = "p-4 rounded-xl text-sm font-medium text-center bg-blue-100 text-blue-700";
                statusBox.innerText = `Enviando e imprimiendo '${file.name}'...`;
                statusBox.classList.remove("hidden");

                try {
                    const response = await fetch("/upload", {
                        method: "POST",
                        body: formData
                    });
                    const result = await response.json();

                    if (response.ok) {
                        statusBox.className = "p-4 rounded-xl text-sm font-medium text-center bg-green-100 text-green-700";
                        statusBox.innerText = `¡Impresión completada para '${file.name}'!`;

                        // Actualizar historial visual
                        const historyList = document.getElementById("history-list");
                        if (historyList.children[0]?.tagName === "SPAN") historyList.innerHTML = "";

                        const item = document.createElement("div");
                        item.className = "flex justify-between items-center bg-gray-50 px-3 py-2 rounded border border-gray-100 text-xs text-gray-700";
                        item.innerHTML = `<span>${file.name}</span> <span class="bg-green-100 text-green-700 px-2 py-0.5 rounded-full font-semibold">Impreso</span>`;
                        historyList.prepend(item);
                    } else {
                        throw new Error(result.detail || "Error desconocido");
                    }
                } catch (error) {
                    statusBox.className = "p-4 rounded-xl text-sm font-medium text-center bg-red-100 text-red-700";
                    statusBox.innerText = `Error: ${error.message}`;
                }
            }
        </script>
    </body>
    </html>
    """


@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Formato no permitido")

    file_path = os.path.join(UPLOAD_DIR, file.filename)
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    try:
        universal_print(file_path)
        return {"status": "success", "filename": file.filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)