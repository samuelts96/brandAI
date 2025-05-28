import os
import json
import base64
import faiss
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from typing import Any
from openai import OpenAI
from agents import Agent, FunctionTool, RunContextWrapper

class DesignAnalyzerAgent(Agent):
    def __init__(self, faiss_index_path: str, doc_chunk_path: str, env_path: str = ".env"):
        load_dotenv(env_path)

        if not os.getenv("OPENAI_API_KEY"):
            raise EnvironmentError("API key not found. Set OPENAI_API_KEY in your .env file.")

        self.client = OpenAI()
        self.model = SentenceTransformer("all-MiniLM-L6-v2")

        if not os.path.exists(faiss_index_path):
            raise FileNotFoundError(f"FAISS index not found at: {faiss_index_path}")
        self.index = faiss.read_index(faiss_index_path)

        if not os.path.exists(doc_chunk_path):
            raise FileNotFoundError(f"Document chunk file not found at: {doc_chunk_path}")
        with open(doc_chunk_path, "r", encoding="utf-8") as f:
            self.doc_chunks = json.load(f)

        tools = [
            FunctionTool(
                name="analyze_image_tool",
                description="Analyze a design image using RAG context and GPT-4o.",
                params_json_schema={
                    "type": "object",
                    "properties": {
                        "image_path": {"type": "string", "description": "Path to the image file"},
                        "query": {"type": "string", "description": "Design query or user instruction"}
                    },
                    "required": ["image_path", "query"],
                    "additionalProperties": False
                },
                on_invoke_tool=self.analyze_image_tool
            )
        ]

        super().__init__(
            name="DesignAnalyzerAgent",
            instructions="You analyze uploaded images like logos and catalogs using retrieved design context.",
            tools=tools,
            model="gpt-4o"
        )

    async def get_context(self, query: str, query_type: str = "general") -> str:
        try:
            if query_type == "logo":
                logo_keywords = ["logo", "brand mark", "identity"]
                query_vec = self.model.encode(["visual identity analysis for logo"])
            elif query_type == "font_color":
                query_vec = self.model.encode(["font and color usage in design"])
            else:
                query_vec = self.model.encode([query])

            _, indices = self.index.search(query_vec, 3)
            return "\n".join([self.doc_chunks[i] for i in indices[0]])
        except Exception as e:
            return f"[ERROR] Could not retrieve context: {e}"

    async def analyze_image_tool(self, ctx: RunContextWrapper[Any], image_path: str, query: str) -> str:
        if not os.path.exists(image_path):
            return f"[ERROR] Image not found: {image_path}"

        try:
            # Determine the type of query
            lowered = query.lower()
            if any(k in lowered for k in ["logo", "branding"]):
                query_type = "logo"
            elif any(k in lowered for k in ["font", "color"]):
                query_type = "font_color"
            else:
                query_type = "general"

            context = await self.get_context(query, query_type=query_type)

            with open(image_path, "rb") as f:
                image_b64 = base64.b64encode(f.read()).decode("utf-8")

            '''prompt_text = (
                f"{context}\n\nAnalyze the uploaded image:\n"
                f"- For logos: describe visual identity, shape, style, and color effectiveness\n"
                f"- For catalogs: assess layout, font readability, color harmony\n"
                f"- If unsure, provide general visual design feedback\n"
                f"Respond clearly and concisely."
            )'''

            '''prompt_text = (
            f"{context}\n\n"
            f"Analyze the uploaded image based on the following query:\n"
            f"{query}\n\n"
            f"If the query is unclear, provide general feedback on:\n"
            f"- Logo design: visual identity, shape, style, color impact\n"
            f"- Catalog layout: organization, font readability, color harmony\n"
            f"- Any notable design strengths or weaknesses\n\n"
            f"Respond clearly and concisely."
         )'''
            prompt_text = (
    f"{context}\n\n"
    f"Analyze the uploaded image based on the following query:\n"
    f"{query}\n\n"
    f"If the query requests color analysis, extract dominant colors and return them as hex codes (e.g., #FF5733)."
    f"If the query requests font analysis, describe the font styles, typefaces, and formatting (e.g., serif/sans-serif, bold, italic)."
    f"If the query involves logos, identify their presence, position, and describe visual characteristics like shape, style, and brand identity cues."
    f"If the query is about layout, provide insights on structure, alignment, spacing, and design hierarchy."
    f"If the query is broad or combines multiple requests, cover each part clearly and concisely."
    f"If the query is unclear, give general design feedback covering colors, typography, logos, and layout.\n\n"
    f"Be specific. Use technical terms where appropriate. Return visual properties in a clear format (e.g., color hex codes, font types, layout patterns)."
)


            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a visual design expert."},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt_text},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}}
                        ]
                    }
                ]
            )

            return response.choices[0].message.content

        except Exception as e:
            return f"[ERROR] Image analysis failed: {e}"