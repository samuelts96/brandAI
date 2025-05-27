import os
import shutil
import tempfile
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from main import DesignAnalyzerAgent

app = FastAPI()

# Initialize your design analyzer agent
agent = DesignAnalyzerAgent(
    faiss_index_path="Vector_Database/faiss_index.index",
    doc_chunk_path="Vector_Database/document_chunks.json"
)

# ✅ Response model
class AnalysisResponse(BaseModel):
    result: str

@app.post("/analyze-image", response_model=AnalysisResponse)
async def analyze_image(file: UploadFile = File(...), query: str = Form(...)):
    try:
        # Save uploaded image
        temp_dir = tempfile.mkdtemp()
        temp_path = os.path.join(temp_dir, file.filename)

        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Run the image analysis tool
        result = await agent.tools[0].on_invoke_tool(
            ctx=None,
            image_path=temp_path,
            query=query
        )

        # ✅ Return as validated JSON
        return AnalysisResponse(result=result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze image: {str(e)}")
