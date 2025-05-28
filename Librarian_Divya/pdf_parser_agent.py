# pdf_agent_handler.py
from agents import (
    Agent, RunContextWrapper, Runner, MessageOutputItem,
    ToolCallItem, ToolCallOutputItem, function_tool, trace, ItemHelpers
)
from pydantic import BaseModel
from typing import Dict
import os
import json
import pdfplumber
import traceback
import uuid
from openai import AsyncOpenAI, OpenAI
from cloudinary_upload import upload_to_cloudinary
from table_tool import extract_tables_info, openai_responses
from dotenv import load_dotenv
from agents import OpenAIChatCompletionsModel

load_dotenv()

MODEL_NAME = "gpt-4.1-nano-2025-04-14"
client = AsyncOpenAI()
openai_client = OpenAI()

class PDFInspectorContext(BaseModel):
    pdf_path: str | None = None

def save_dict_to_json(data, filename="image_links.json"):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
    return filename

@function_tool
async def save_text_tool(context: RunContextWrapper[PDFInspectorContext]) -> str:
    file_path = context.context.pdf_path
    assert file_path, "PDF path not set."

    extracted_text: Dict[int, str] = {}

    if file_path.lower().endswith(".pdf"):
        with pdfplumber.open(file_path) as pdf:
            for page_no, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text:
                    extracted_text[page_no + 1] = text
    else:
        raise ValueError("Unsupported file type.")

    return f"Text saved at: {save_dict_to_json(extracted_text, filename='extracted_text.json')}"

@function_tool
def save_image_tool(context: RunContextWrapper[PDFInspectorContext]) -> dict[str, str]:
    pdf_path = context.context.pdf_path
    assert pdf_path, "PDF path not set."
    try:
        image_info_dict = upload_to_cloudinary(pdf_path)
        save_dict_to_json(image_info_dict)
        return image_info_dict
    except Exception:
        traceback.print_exc()
        return {"error": "Error occurred during image extraction."}

@function_tool
def save_table_tool(context: RunContextWrapper[PDFInspectorContext]) -> str:
    pdf_path = context.context.pdf_path
    assert pdf_path, "PDF path not set."

    tables_json = []
    for img_path in extract_tables_info(pdf_path)[:20]:
        response = openai_responses(openai_client, img_path)
        tables_json.append(response.output[0].content[0].text)

    filename = save_dict_to_json(tables_json, filename="filtered_tables_output.json")
    return f"Filtered tables written to {filename}"

class PDFAgentHandler:
    def __init__(self):
        self.context = PDFInspectorContext()
        self.input_items = []

        self.agent = Agent[PDFInspectorContext](
            name="PDF AI",
            handoff_description="PDF parsing assistant",
            instructions="""
                You are a helpful assistant for analyzing PDF documents.

                Use the tools ONLY when asked:
                - Use save_text_tool to extract text
                - Use save_image_tool to extract images
                - Use save_table_tool to extract tables

                Do not answer questions beyond the tool scope.
                Do not use tools unless PDF is loaded and user asks.
            """,
            tools=[save_text_tool, save_image_tool, save_table_tool],
            model=OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=client),
        )

    def set_pdf(self, pdf_path: str):
        self.context.pdf_path = pdf_path
        self.input_items = []

    async def process_query(self, query: str) -> list[str]:
        conversation_id = uuid.uuid4().hex[:16]
        self.input_items.append({"content": query, "role": "user"})

        with trace("PDFInspector", group_id=conversation_id):
            result = await Runner.run(self.agent, self.input_items, context=self.context)

            new_responses = []
            for item in result.new_items:
                if isinstance(item, MessageOutputItem):
                    new_responses.append(f"{item.agent.name}: {ItemHelpers.text_message_output(item)}")
                elif isinstance(item, ToolCallItem):
                    new_responses.append(f"{item.agent.name}: Calling a tool...")
                elif isinstance(item, ToolCallOutputItem):
                    new_responses.append(f"{item.agent.name}: Tool result -> {item.output}")
                else:
                    new_responses.append(f"{item.agent.name}: Skipping item: {item.__class__.__name__}")

            self.input_items = result.to_input_list()
            self.agent = result.last_agent
            return new_responses
