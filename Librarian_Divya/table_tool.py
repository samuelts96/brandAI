from ultralytics import YOLO
from pathlib import Path
import cv2
import fitz 
import os

# def pdf_to_images_pymupdf(pdf_path, output_folder="pdf_pages", dpi=150):
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

# # pdf_path = "xyz.pdf"
# # image_paths = pdf_to_images_pymupdf(pdf_path)

# def extract_table(pdf_path: str) -> list:
#     tables = []
#     with pdfplumber.open(pdf_path) as pdf:
#         for i, page in enumerate(pdf.pages):
#             extracted = page.extract_tables()
#             for table in extracted:
#                 tables.append({"page": i + 1, "table": table})
#     return tables

# def is_non_empty_cell(cell):
#     return cell is not None and str(cell).strip() != ""

# def clean_table(table_data):
#     cleaned_rows = [row for row in table_data if any(is_non_empty_cell(cell) for cell in row)]

#     if not cleaned_rows:
#         return None

#     if len(cleaned_rows) <= 2:
#         has_real_content = any(
#             any(is_non_empty_cell(cell) for cell in row)
#             for row in cleaned_rows
#         )
#         return cleaned_rows if has_real_content else None

#     return cleaned_rows

# def filter_tables(output):
#     filtered_tables = []
#     for element in output:
#         cleaned = clean_table(element['table'])
#         if cleaned:
#             filtered_tables.append({
#                 "page": element["page"],
#                 "table": cleaned
#             })
#     return filtered_tables


# def write_tables_to_json(filtered_tables, filename="filtered_tables_output.json"):
#     with open(filename, "w", encoding="utf-8") as file:
#         json.dump(filtered_tables, file, ensure_ascii=False, indent=4)

import base64
from ultralytics import YOLO
from pathlib import Path
import cv2
import fitz 
import os
import aspose.words as aw
import json

def save_dict_to_json(data, filename="image_links.json"):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
    
    return filename

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

def save_pictures_from_results(page_number, results, output_dir="output/pictures"):
    img = results.orig_img
    boxes = results.boxes
    names = results.names

    all_images = []

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    pic_id = 0

    for box, cls in zip(boxes.xyxy.cpu().numpy(), boxes.cls.cpu().numpy()):
        class_name = names[int(cls)]

        if class_name == "Table":
            x1, y1, x2, y2 = map(int, box)
            cropped_img = img[y1:y2, x1:x2]

            filename = output_path / f"page-{page_number + 1}_table-{pic_id}.jpg"
            cv2.imwrite(str(filename), cropped_img)
            print(f"Saved: {filename}")
            pic_id += 1
            all_images.append(str(filename))
    if pic_id == 0:
        print(f"No pictures found on page {page_number}.")
    return all_images


def extract_tables_info(pdf_path):
    model_path = r"yolov8n-doclaynet.pt"

    images_folder = convert_pdf_to_images(pdf_path)

    extracted_table = []
    for page_number, image_path in enumerate(images_folder):
        img = cv2.imread(image_path, cv2.IMREAD_COLOR)
        model = YOLO(model_path)

        result = model.predict(img)[0]
        all_tables = save_pictures_from_results(page_number, result, output_dir="output/tables")
        extracted_table.extend(all_tables)

    return extracted_table


def encode_image(image_path):
  with open(image_path, "rb") as image_file:
    return base64.b64encode(image_file.read()).decode('utf-8')

def openai_responses(open_ai_client,image_path):

    user_input = image_path.split('/')[-1].split('.')[0]
    base64_image = encode_image(image_path)
    response = open_ai_client.responses.create(
        model="gpt-4.1-nano-2025-04-14",
        input=[
            {
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": "You will receive an image and a page number along with an image number\n--------------------------------------------------------\nYou have to return a json which contains,\n\ntable > boolean\npage number > int\ntable number > int\nrows > list[tuple]\ndescription > str\n--------------------------------------------------------\nAdditional Instructions: \n\n*** A table is a collection of rows and columns ***\n\n1) return each row as a tuple\n2) all tuples should contain same number of elements\n3) if there are empty values in the table then replace it with NaN\n4) if the given image does not contain a table return a json with the 'table' parameter as false and the others as empty \n5) treat headers as a row\n6) brief summary/description of the table in 1 or 2 sentences\n"}
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_image",
                        "image_url": f"data:image/png;base64,{base64_image}",
                    },
                    {
                        "type": "input_text",
                        "text": f"{user_input}",
                    }]
            }
        ],
    )

    return response