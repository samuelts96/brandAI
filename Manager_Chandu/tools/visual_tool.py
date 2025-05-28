import httpx
import traceback
from agents import function_tool

@function_tool()
async def analyze_image(image_path: str, query: str) -> str:
    """
    Analyze the content of an image based on a user query.
    Use this tool if the user provides an image and asks questions like:
    - What colors are used?
    - Is there a logo?
    - What font or design elements are present?
    Requires both a query and a valid image file path.
    """
    try:
        with open(image_path, "rb") as f:
            files = {"file": (image_path, f, "image/png")}
            data = {"query": query}
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "http://localhost:6040/analyze-image",
                    files=files,
                    data=data
                )
        if response.status_code == 200:
            return response.json().get("result", "No result from sub-agent.")
        else:
            return f"Error: {response.status_code} - {response.text}"
    except Exception as e:
        return f"Tool error: {str(e)}\n{traceback.format_exc()}"