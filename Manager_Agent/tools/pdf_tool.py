import httpx
import traceback
import os
from agents import function_tool

@function_tool()
async def analyze_pdf(pdf_path: str = None, query: str = "") -> str:
    """
    Optionally uploads a PDF, sends a query, and handles the response.
    If the response is an image URL, downloads it and returns the filename.
    Otherwise, returns the response text.
    """
    try:
        # Step 1: Upload PDF (if provided)
        if pdf_path:
            with open(pdf_path, "rb") as f:
                files = {"file": (os.path.basename(pdf_path), f, "application/pdf")}
                async with httpx.AsyncClient(timeout=60.0) as client:
                    upload_response = await client.post(
                        "https://4e92-82-7-117-241.ngrok-free.app/upload_pdf/",
                        files=files
                    )
            if upload_response.status_code != 200:
                return f"Upload Error: {upload_response.status_code} - {upload_response.text}"

        data = {"query": query}
        async with httpx.AsyncClient(timeout=60.0) as client:
            chat_response = await client.post(
                "https://4e92-82-7-117-241.ngrok-free.app/chat/",
                data=data
            )
        if chat_response.status_code != 200:
            return f"Chat Error: {chat_response.status_code} - {chat_response.text}"

        # Step 3: Parse and handle the response
        result_json = chat_response.json()
        result = result_json.get("response", [""])[0].strip()

        if result.startswith("http") and result.endswith((".jpg", ".jpeg", ".png", ".webp")):
            filename = os.path.basename(result)
            async with httpx.AsyncClient(timeout=60.0) as client:
                image_response = await client.get(result)
                if image_response.status_code == 200:
                    with open(filename, "wb") as f:
                        f.write(image_response.content)
                    return filename
                else:
                    return f"Failed to download image: {image_response.status_code} - {image_response.text}"

        return result

    except Exception as e:
        return f"Tool error: {str(e)}\n{traceback.format_exc()}"
