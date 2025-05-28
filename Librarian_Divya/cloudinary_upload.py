# from ultralytics import YOLO
# import cv2
# import fitz 
# from PIL import Image
# from io import BytesIO

# import tempfile
# import os
# import cloudinary
# import cloudinary.uploader
# import dotenv



# cloudinary.config(
#     cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
#     api_key=os.getenv("CLOUDINARY_API_KEY"),
#     api_secret=os.getenv("CLOUDINARY_API_SECRET"),
# )


# def save_image_temporarily(image, filename="temp_image.png"):
#     temp_dir = tempfile.mkdtemp()
#     file_path = os.path.join(temp_dir, filename)
#     image.save(file_path)
#     return file_path

# def upload_to_cloudinary(pdf_path: str) -> dict:

    
#     doc = fitz.open(pdf_path)
#     image_info = {}

#     for page_index in range(len(doc)):
#         page = doc[page_index]
#         images = page.get_images(full=True)
#         for img_index, img in enumerate(images):

#             xref = img[0]
#             base_image = doc.extract_image(xref)
#             image_bytes = base_image["image"]
#             temp_image_name = f'pageid_{page_index+1}_imgid_{img_index}'
#             image_file_name = f'_{page_index+1}_{img_index}.png'
            
#             image = Image.open(BytesIO(image_bytes))
#             image_temp_file_path = save_image_temporarily(image, image_file_name)
#             folder_name = 'new_pdf_parser'

#             upload_result = cloudinary.uploader.upload(image_temp_file_path,
#                                                     public_id=temp_image_name,asset_folder=folder_name)
            
#             print(upload_result["secure_url"])
#             image_info[image_file_name] = upload_result["secure_url"]

#     doc.close()
#     return image_info

from ultralytics import YOLO
import cloudinary.uploader
import aspose.words as aw
from pathlib import Path
import cloudinary
import dotenv
import fitz 
import cv2
import os
import base64

dotenv.load_dotenv()

def encode_image(image_path):
  with open(image_path, "rb") as image_file:
    return base64.b64encode(image_file.read()).decode('utf-8')
  
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
)

def save_pictures_from_results(page_number, results,openai_response='description', output_dir="output/pictures"):
    img = results.orig_img
    boxes = results.boxes
    names = results.names

    all_images = []

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    pic_id = 0

    for box, cls in zip(boxes.xyxy.cpu().numpy(), boxes.cls.cpu().numpy()):
        class_name = names[int(cls)]

        if class_name == "Picture":
            x1, y1, x2, y2 = map(int, box)
            cropped_img = img[y1:y2, x1:x2]

            filename = output_path / f"page-{page_number + 1}_pic-{pic_id}.jpg"
            cv2.imwrite(str(filename), cropped_img)
            # print(f"Saved: {filename}")
            pic_id += 1
            all_images.append([str(filename),openai_response])
    if pic_id == 0:
        # print(f"No pictures found on page {page_number}.")
        pass
    return all_images


# def convert_pdf_to_images(pdf_path, output_folder="pdf_pages", dpi=300):
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


def openai_responses(open_ai_client,image_path):

    base64_image = encode_image(image_path)
    response = open_ai_client.responses.create(
        model="gpt-4.1-nano-2025-04-14",
        input=[
            {
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": "You will receive an image\n--------------------------------------------------------\nYou have to return a str which contains\n\n description > str, ex: 'this image describption' \n--------------------------------------------------------\nDescription should be short and concise about the image\n\n"}
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
                        "text": "describe",
                    }]
            }
        ],
    )

    return response

def upload_to_cloudinary(pdf_path,openai_client) -> dict:
    model_path = r"yolov8n-doclaynet.pt"

    images_folder = convert_pdf_to_images(pdf_path)

    extracted_imgs_path = []
    for page_number, image_path in enumerate(images_folder):
        img = cv2.imread(image_path, cv2.IMREAD_COLOR)
        # base64_image = encode_image(image_path)
        response = openai_responses(openai_client,image_path)
        # print(response.output[0].content[0])
        openai_response = response.output[0].content[0].text
        print('*'*50)


        model = YOLO(model_path)

        result = model.predict(img)[0]
        all_imgs = save_pictures_from_results(page_number, result,openai_response=openai_response, output_dir="output/pictures")
        extracted_imgs_path.extend(all_imgs)

    # print(extracted_imgs_path)
    image_info = {}

    folder_name = 'new_pdf_parser'

    for single_element in extracted_imgs_path:  
        single_image_path = single_element[0]
        public_id = single_image_path.split('\\')[-1].split('.')[0]
        upload_result = cloudinary.uploader.upload(single_image_path,
                                                public_id=public_id,asset_folder=folder_name)
        # print(upload_result["secure_url"])
        image_info[single_image_path] = [upload_result["secure_url"],single_element[1]]
    return image_info