import httpx
import traceback
from agents import function_tool
import asyncio
import os

@function_tool()
async def bookkeeper(csv_file: str = None, query: str = None) -> str:
    try:
        if csv_file is None or csv_file == '':
            data = {"query": query}
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "https://b8f7-157-130-87-238.ngrok-free.app/bookkeeper",
                    data=data
                )
        else:
            with open(csv_file, "rb") as f:
                file = {"file": (os.path.basename(csv_file), f, "text/csv")}
                data = {"query": query}
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(
                        "https://b8f7-157-130-87-238.ngrok-free.app/bookkeeper",
                        files=file,
                        data=data
                    )

        for key, value in response.headers.items():
            if key.lower().startswith("x-"):
                val=f"  {key}: {value}"

        content_type = response.headers.get("Content-Type", "")
        if response.status_code == 200:
            if "application/json" in content_type:
                return response.json().get("response", "No result from sub-agent.")
            else:
                output_file = "graph.png"
                if "Content-Disposition" in response.headers:
                    import re
                    match = re.search('filename="(.+)"', response.headers["Content-Disposition"])
                    if match:
                        output_file = match.group(1)
                with open(output_file, "wb") as f:
                    f.write(response.content)
                return f"File received and saved as: {output_file}"
        else:
            return f"Error: {response.status_code} - {response.text}"
    except Exception as e:
        return f"Tool error: {str(e)}\n{traceback.format_exc()}"



async def test_home() -> str:
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(
                "https://53c4-96-89-67-41.ngrok-free.app/"

            )
        if response.status_code == 200:
            return response.text
            #return response.json().get("result", "No result from sub-agent.")
        else:
            return f"Error: {response.status_code} - {response.text}"
    except Exception as e:
        return f"Tool error: {str(e)}\n{traceback.format_exc()}"
    

