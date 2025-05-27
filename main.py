import uvicorn
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from pdf_parser_agent import PDFAgentHandler
import uuid
import os
import traceback

app = FastAPI(
    middleware=[
        Middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    ]
)

agent_handler = PDFAgentHandler()

@app.post("/upload_pdf/")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.lower().endswith((".pdf", ".doc", ".docx")):
        return JSONResponse({"error": "Invalid file format. Please upload a PDF or DOCX."}, status_code=400)
    try:
        ext = os.path.splitext(file.filename)[1].lower()
        file_path = f"temp_{uuid.uuid4().hex[:8]}{ext}"

        with open(file_path, "wb") as f:
            f.write(await file.read())

        agent_handler.set_pdf(file_path)
        return JSONResponse({"message": f"PDF '{file.filename}' uploaded and ready."}, status_code=200)
    except Exception as e:
        traceback.print_exc()
        return JSONResponse({"error": f"Error uploading file: {e}"}, status_code=500)

@app.post("/chat/")
async def chat(query: str = Form(...)):
    if not agent_handler.context.pdf_path:
        return JSONResponse({"error": "Please upload a PDF file first."}, status_code=400)

    try:
        response = await agent_handler.process_query(query)
        return JSONResponse({"response": response}, status_code=200)
    except Exception as e:
        traceback.print_exc()
        return JSONResponse({"error": f"Error processing query: {e}"}, status_code=500)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
