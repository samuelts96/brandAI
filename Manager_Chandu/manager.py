import asyncio
from agents import Agent, Runner
from tools.visual_tool import analyze_image
from tools.pdf_tool import analyze_pdf
from logo import extract_logos_from_pdf
from tools.pdf_file import save_query_result_to_pdf
from tools.csv_tool import bookkeeper
import os
from dotenv import load_dotenv

load_dotenv()

session_cache = {
    "logo_path": None,
    "image_path": None ,
    "csv_path":None,
    "image_used":None
}

def reset_session_cache():
    for key in session_cache:
        session_cache[key] = None
    last_pdf_path["value"] = None
    pdf_path = "analysis_file.pdf"
    try:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
    except:
        pass

def print_cached_image_paths():
    print("\nCached Image Paths:")
    for label, path in session_cache.items():
        if path:
            print(f"{label}: {path}")
def is_csv_file(path):
    return path and path.lower().endswith(".csv")
last_pdf_path = {"value": None}

def extract_image_path(text):
    import re
    pattern = r"(?:Saved as:|saved at:)?\s*([\w./\\-]+\.png)"
    matches = re.findall(pattern, text, re.IGNORECASE)
    return matches[-1] if matches else None

manager_agent = Agent(
    name="ManagerAgent",
    model="gpt-4o",
    instructions="""
You are a Manager Agent.
-first follow the instructions if in query requested for the path please only provide the path only  .
-about the analyze_pdf can also accepts only query also .
- When a new PDF is uploaded:
    - Run extract_logos_from_pdf and analyze_pdf concurrently.
    - Cache the returned logo_path.
    - Classify the query into one of: 'extract logo', 'extract image', 'extract table', 'extract text'.
    - If 'extract logo': use extract_logos_from_pdf result.
    - Else: send only the classified query (no PDF) to analyze_pdf.
    - Use the returned image path with analyze_image and the original query.
    
- If the no PDF is provided :
    - Classify the query into one of the  'extract logo', 'extract image', 'extract table', 'extract text'. types.
    - If 'extract logo': use cached logo_path with analyze_image.
    - Else: send only the classified query to analyze_pdf for query argument.
    - Then forward returned image path + original query to analyze_image.

- If a PNG/JPG is uploaded:
    - Use analyze_image directly with the image and query.
- If this is the first CSV upload:
    - Send both csv_file and query to the bookkeeper tool.
    - Cache the csv_file path.

- If the CSV has already been uploaded:
    - Send only the query to the bookkeeper tool (omit the file).

- The bookkeeper tool may return:
    - Only a response (text-based answer), or
    - Both an image and a response.

- In either case, return:
    1. response (text)
    2. image_path (or None if no image is generated)

- Always return the raw result from analyze_image.
""",
    tools=[analyze_image, analyze_pdf, extract_logos_from_pdf,bookkeeper]
)

async def run_manager_agent(query: str, path: str = None) -> str:
    csv_check = await Runner.run(
    starting_agent=manager_agent,
    input=(
        f"""File path: {path if path else 'None'}
Query: {query}

Instructions:
You are a task classifier. Your job is to decide whether the task involves analyzing a CSV file.

Rules:
- If the file path ends with `.csv`, this is CSV analysis task.
- If the query contains language about:
-Any calculations
-Quantity
  - data or 
  - tables
  - rows or columns
  - trends
  - summaries of report sales or graph
  - averages or totals
  - categories or rankings
  - numeric patterns
  -time Series 
  then it's also likely a CSV analysis task.

  
- If the path does NOT end in `.csv` and the query refers to images, logos, colors, layouts, or visual design — it's NOT a CSV analysis task.

Output:
Return ONLY one word — either:
  → CSV
  → NOT

Do NOT explain or describe anything else.
"""
    ))
    result = csv_check.final_output.strip().lower()
    if(result=="csv"):
        if path and is_csv_file(path):
            session_cache["csv_path"] = path
            full_input = (
                f"CSV_ANALYSIS_TASK_FIRST_TIME\n"
                f"File path: {path}Query: {query}  \n"
                f"Please analyze the uploaded CSV file using the bookkeeper tool.\n"
                f"if returned path just return only path ,if response return response "
                
            )
        elif session_cache["csv_path"]:
            full_input = (
                f"CSV_ANALYSIS\n"
                f"csv file path {session_cache["csv_path"]}  use this path Query: {query} \n"
                f"Please analyze the uploaded CSV file using the bookkeeper tool."
                f"if returned path just return only path ,if response return response"
            )
        else:
            return "Please upload a CSV file before submitting a query."
        response = await Runner.run(starting_agent=manager_agent, input=full_input)
        text = response.final_output
        image_path = extract_image_path(text)
        session_cache["image_used"] = image_path
        if image_path:
            cleaned_text = text.replace(f"File received and saved as: {image_path}", "").strip()
            save_query_result_to_pdf(query, image_path, result_text=cleaned_text)
            return image_path
        else:
            save_query_result_to_pdf(query, None, result_text=text)
            return text

    try:
        if path and path.lower().endswith(".pdf"):
            if path != last_pdf_path["value"]:
                # reset_session_cache()
                last_pdf_path["value"] = path
                logo_task = Runner.run(starting_agent=manager_agent, input=f"Extract logos from PDF: {path}.\n"
                                       f"Return ONLY the path of the saved logo image file. "
                                       f"Do not include any descriptions or no futher image_analysis")
                pdf_prewarm_task = Runner.run(starting_agent=manager_agent, input=f"extract image from PDF: {path}\n"
                                       f"Return ONLY the path of the saved logo image file. "
                                       f"Do not include any descriptions or analysis.")
                logo_result, prewarm_result = await asyncio.gather(logo_task, pdf_prewarm_task)
                logo_path = logo_result.final_output.strip()
                session_cache["logo_path"] = logo_path
                prewarm_path = prewarm_result.final_output.strip()
            classification_prompt = f"Classify the following query into one of: extract logo, extract image, extract table, extract text: '{query}'"
            classification = await Runner.run(starting_agent=manager_agent, input=classification_prompt)
            classified = classification.final_output.strip().lower()

            if 'logo' in classified:
                session_cache["image_used"]=session_cache['logo_path']
                result = await Runner.run(
                    starting_agent=manager_agent,
                    input=f"{query} The image is located at {session_cache['logo_path']}"
                )
            else:
                pdf_result = await Runner.run(
                    starting_agent=manager_agent,
                    input=f"{classified} — send this to the analyze_pdf tool as the query only. Return only the extracted image path."
                )
                image_path = pdf_result.final_output.strip()
                session_cache["image_used"]=image_path 
                result = await Runner.run(
                    starting_agent=manager_agent,
                    input=f"{query} The image is located at {image_path}"
                )

        elif path and path.lower().endswith(('.png', '.jpg', '.jpeg')):
            session_cache["image_path"] = path
            result = await Runner.run(
                starting_agent=manager_agent,
                input=f"{query} The image is located at {path}."
            )
            save_query_result_to_pdf(query=query,image_path=path,result_text=result.final_output)
            return result.final_output


        elif last_pdf_path["value"]:
            classification_prompt = f"Classify the following query into one of: extract logo, extract image, extract table, extract text: '{query}'"
            classification = await Runner.run(starting_agent=manager_agent, input=classification_prompt)
            classified = classification.final_output.strip().lower()
            if 'logo' in classified:
                if session_cache["logo_path"]:
                    print(f"5. Using cached logo path: {session_cache['logo_path']}")
                    
                else:
                    logo_result = await Runner.run(
                        starting_agent=manager_agent,
                        input=(
        f"Extract logos from PDF: {last_pdf_path['value']}.\n"
        f"Return ONLY the path of the saved logo image file. "
        f"Do not include any descriptions or analysis."
    )
)
                    logo_path = logo_result.final_output.strip()
                    if logo_path.lower().endswith(('.png', '.jpg', '.jpeg')):
                        session_cache["logo_path"] = logo_path
                        print(f"Re-extracted and cached logo path: {logo_path}")
                    else:
                        return "Logo extraction failed. Please check the PDF."
                session_cache["image_used"]=session_cache['logo_path']
                result = await Runner.run(
                    starting_agent=manager_agent,
                    input=f"{query} The image is located at {session_cache['logo_path']}"
                )
            else:
                pdf_result = await Runner.run(
                    starting_agent=manager_agent,
                    input=f"{classified} — send this to the analyze_pdf tool as the query only.Return ONLY the path of the saved logo image file.Do not include any descriptions or analysis.")
                image_path = pdf_result.final_output.strip()
                
                if not image_path.lower().endswith(('.png', '.jpg', '.jpeg')):
                    return f"Invalid image path returned from analyze_pdf: {image_path}"
                session_cache["image_used"]=image_path
                result = await Runner.run(
                    starting_agent=manager_agent,
                    input=f"{query} The image is located at {image_path}"
                )

        elif session_cache["image_path"]:
            image_path=session_cache["image_path"]
            session_cache["image_used"]=image_path
            result = await Runner.run(
                starting_agent=manager_agent,
                input=f"{query} The image is located at {session_cache['image_path']}"
            )

        else:
            return "Please upload a PDF or image first."

        if session_cache["image_used"] is not None and session_cache["image_used"].startswith("./"):
            save_query_result_to_pdf(query=query,image_path=session_cache["image_used"][2:],result_text=result.final_output)
        else:
            save_query_result_to_pdf(query=query,image_path=session_cache["image_used"],result_text=result.final_output)
        return result.final_output

    except Exception as e:
        return f"Agent execution failed: {e}"
