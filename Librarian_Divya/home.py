from __future__ import annotations as _annotations

import cloudinary.uploader
from starlette.middleware.cors import CORSMiddleware
from fastapi import FastAPI, File, UploadFile, Form
from agents import OpenAIChatCompletionsModel
from starlette.middleware import Middleware
from fastapi.responses import JSONResponse
from openai import AsyncOpenAI, OpenAI
from pydantic import BaseModel
from typing import Dict

from cloudinary_upload import *
from table_tool import *

import pdfplumber
import subprocess
import cloudinary
import traceback
import uvicorn
import dotenv
import json
import uuid
import os

from agents import (
    Agent,
    RunContextWrapper,
    Runner,
    MessageOutputItem,
    ToolCallItem,
    ToolCallOutputItem,
    ItemHelpers,
    function_tool,
    trace,
)

# def convert_pdf_to_images(pdf_path, output_folder="pdf_pages", dpi=150):
#     os.makedirs(output_folder, exist_ok=True)
#     doc = fitz.open(pdf_path)
#     image_paths = []

#     for page_num in range(len(doc)):
#         page = doc.load_page(page_num)
#         pix = page.get_pixmap(dpi=dpi)
#         img_path = os.path.join(output_folder, f"page_{page_num + 1}.png")
#         pix.save(img_path)
#         image_paths.append(img_path)

#     return image_paths

def save_dict_to_json(data, filename="image_links.json"):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
    
    return filename

dotenv.load_dotenv()

MODEL_NAME = "gpt-4.1-nano-2025-04-14"
client = AsyncOpenAI()
openai_client = OpenAI()

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
)

class PDFInspectorContext(BaseModel):
    pdf_path: str | None = None   

@function_tool
async def save_text_tool(context: RunContextWrapper[PDFInspectorContext]) -> str:
    assert context.context.pdf_path, "PDF path not set. Please provide a valid file first."
    file_path = context.context.pdf_path
    extracted_text: Dict[int, str] = {}

    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        with pdfplumber.open(file_path) as pdf:
            for page_no, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text:
                    extracted_text[page_no + 1] = text

    elif ext in [".docx", ".doc"]:
        doc = aw.Document(file_path)
        # for i in range(doc.page_count):
            # extractor = aw.layout.LayoutCollector(doc)
            # start = extractor.get_start_page_index(doc.get_child_nodes(aw.NodeType.PARAGRAPH, True)[0])
        text = doc.get_text()
            # Get text from the page using text extraction with page range
            # text = doc.extract_text(aw.saving.sPageSet(i))
        extracted_text_plain = text.strip()
        extracted_text = {1: extracted_text_plain}  # Assuming single page for simplicity
    else:
        raise ValueError("Unsupported file type for text extraction.")

    text_path = save_dict_to_json(extracted_text, filename="extracted_text.json")

    image_links = convert_pdf_to_images(file_path, output_folder="pdf_pages", dpi=300)
    print('*' * 50)
    print(image_links)
    folder_name = 'new_pdf_parser'
    public_id = image_links[0].split('\\')[-1].split('.')[0]  # Extract filename without extension
    upload_result = cloudinary.uploader.upload(image_links[0],
                                                public_id=public_id,asset_folder=folder_name)
    # image_info_dict = upload_to_cloudinary(image_links[0], openai_client)
    
    # print(image_info_dict)

    # return f"Text saved at: {text_path}"
    return upload_result["secure_url"]

def convert_pdf_to_images(file_path, output_folder="pdf_pages", dpi=300):
    os.makedirs(output_folder, exist_ok=True)
    image_paths = []

    file_ext = os.path.splitext(file_path)[1].lower()

    if file_ext == ".pdf":
        doc = fitz.open(file_path)
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            pix = page.get_pixmap(dpi=dpi)
            img_path = os.path.join(output_folder, f"page_{page_num + 1}.png")
            pix.save(img_path)
            image_paths.append(img_path)

    elif file_ext in [".doc", ".docx"]:
        doc = aw.Document(file_path)
        save_options = aw.saving.ImageSaveOptions(aw.SaveFormat.JPEG)
        save_options.vertical_resolution = dpi
        save_options.horizontal_resolution = dpi

        for page in range(doc.page_count):
            save_options.page_set = aw.saving.PageSet(page)
            img_path = os.path.join(output_folder, f"page_{page + 1}.jpg")
            doc.save(img_path, save_options)
            image_paths.append(img_path)

    else:
        raise ValueError("Unsupported file type. Only .pdf, .doc, and .docx are supported.")

    return image_paths


@function_tool
def save_image_tool(context: RunContextWrapper[PDFInspectorContext]) -> dict[str,str]:
    try:
        assert context.context.pdf_path, "PDF path not set. Please provide a valid file first."
        pdf_path = context.context.pdf_path
        image_info_dict = upload_to_cloudinary(pdf_path,openai_client)


        # image_info_dict = upload_to_cloudinary(pdf_path)
        filename = save_dict_to_json(image_info_dict)
        # print(f"Image links saved to {filename}")
        # return f'Image links saved to {filename}'
        # return image_info_dict[image_info_dict.keys()[0]]  
        # return 'page-0_pic-0.jpg'
        data = image_info_dict
        # return image_info_dict[list(image_info_dict.keys())[0]][0]
        return data[list(data.keys())[0]][0]
    
    except Exception:
        traceback.print_exc()
        return ["Error occurred during image extraction."]
    
@function_tool
def save_table_tool(context: RunContextWrapper[PDFInspectorContext]) -> str:
    assert context.context.pdf_path, "PDF path not set. Please provide a valid file first."
    pdf_path = context.context.pdf_path
    filename = "filtered_tables_output.json"
    extract_tables = extract_tables_info(pdf_path)
    tables_json = []
    # for img_path in extract_tables[0]:

    #     response = openai_responses(openai_client,img_path)
    #     tables_json.append(response.output[0].content[0].text)
    # filename = save_dict_to_json(tables_json, filename=filename)
    # return f"Filtered tables written to {filename}"
    # image_path=  'output/tables/page-1_table-0.jpg'
    image_path = extract_tables[0] # Assuming the first image path
    result = cloudinary.uploader.upload(image_path, 
                                        public_id='table_image',
                                        asset_folder='new_pdf_parser')
    return result["secure_url"]

pdf_agent = Agent[PDFInspectorContext](
    name="PDF AI",
    handoff_description="PDF parsing assistant",
    instructions="""
    You are a helpful assistant for analyzing PDF documents.

    You do the following: 

    > Use save_text_tool to extract text from the PDF.
    > Use save_image_tool to extract images from the PDF.
    > Use save_table_tool to extract tables from the PDF.

    You are conversational and helpful.

    Use the tool only when asked to perform a specific action.

    You are not allowed to perform any other actions or make any assumptions about the user's intent.
    You are not allowed to answer questions outside the scope of the tools provided.
    You are not allowed to use your own knowledge or any external resources.

    Do not use the tools unless explicitly asked to do so.

    Always make sure a PDF is loaded first.
    """,
    tools=[save_text_tool, save_image_tool, save_table_tool],
    model=OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=client),
)

app = FastAPI(
    middleware=[
        Middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Allows all origins
            allow_credentials=True,
            allow_methods=["*"],  # Allows all methods
            allow_headers=["*"],  # Allows all headers
        )
    ]
)

agent_state = {"context": PDFInspectorContext(), "input_items": [], "current_agent": pdf_agent}

@app.post("/upload_pdf/")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.lower().endswith((".pdf", ".doc", ".docx")):
        return JSONResponse({"error": "Invalid file format. Please upload a PDF, DOC, or DOCX file."}, status_code=400)
    try:
        ext = os.path.splitext(file.filename)[1].lower()

        file_path = f"temp_{uuid.uuid4().hex[:8]}.{ext}"
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        agent_state["context"].pdf_path = file_path
        agent_state["input_items"] = []  
        return JSONResponse({"message": f"PDF '{file.filename}' uploaded and ready for processing."}, status_code=200)
    except Exception as e:
        traceback.print_exc()
        return JSONResponse({"error": f"Error uploading PDF: {e}"}, status_code=500)

@app.post("/chat/")
async def chat(query: str = Form(...)):
    if not agent_state["context"].pdf_path:
        return JSONResponse({"error": "Please upload a PDF file first."}, status_code=400)

    conversation_id = uuid.uuid4().hex[:16]
    agent_state["input_items"].append({"content": query, "role": "user"})

    try:
        with trace("PDFInspector", group_id=conversation_id):
            result = await Runner.run(
                agent_state["current_agent"],
                agent_state["input_items"],
                context=agent_state["context"]
            )

            new_responses = []
            for item in result.new_items:
                agent_name = item.agent.name
                # if isinstance(item, MessageOutputItem):
                    # new_responses.append(f"{agent_name}: {ItemHelpers.text_message_output(item)}")
                # elif isinstance(item, ToolCallItem):
                #     new_responses.append(f"{agent_name}: Calling a tool...")
                if isinstance(item, ToolCallOutputItem):
                    # new_responses.append(f"{item.output}")
                    new_responses.append(f"{item.output}")
                # else:
                    # new_responses.append(f"{agent_name}: Skipping item: {item.__class__.__name__}")

            agent_state["input_items"] = result.to_input_list()
            agent_state["current_agent"] = result.last_agent
            return JSONResponse({"response": new_responses}, status_code=200)

    except Exception as err:
        traceback.print_exc()
        return JSONResponse({"error": f"Unexpected error: {err}"}, status_code=500)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)