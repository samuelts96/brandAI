import os
import fitz
from PIL import Image
from google.cloud import vision
import torch
import torchvision.transforms as transforms
from torchvision.models import resnet18
from torch.nn.functional import cosine_similarity
from agents import function_tool
image_cache={}

@function_tool()
async def extract_logos_from_pdf(pdf_path: str) -> list:
    """
    Process the PDF and extract unique logos .
    Returns a list of saved logo image paths.
    """
    credentials_path = "rock-data-408903-2f439cd20b71.json"
    confidence_threshold = 0.90
    similarity_threshold = 0.60
    pages_dir = "pdf_pages"
    logos_dir = "."
    max_pages = 5
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
    os.makedirs(pages_dir, exist_ok=True)
    os.makedirs(logos_dir, exist_ok=True)
    client = vision.ImageAnnotatorClient()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    base_model = resnet18(pretrained=True)
    model = torch.nn.Sequential(*list(base_model.children())[:-1])
    model.eval().to(device)

    preprocess = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406],
                             std=[0.229, 0.224, 0.225]),
    ])

    embeddings = []
    saved_paths = []
    doc = fitz.open(pdf_path)

    def get_embedding(image: Image.Image) -> torch.Tensor:
        tensor = preprocess(image.convert("RGB")).unsqueeze(0).to(device)
        with torch.no_grad():
            features = model(tensor).squeeze()
        return features.view(-1)

    def is_similar(new_emb: torch.Tensor) -> bool:
        for emb in embeddings:
            sim = cosine_similarity(new_emb.unsqueeze(0), emb.unsqueeze(0)).item()
            if sim >= similarity_threshold:
                return True
        return False

    for i, page in enumerate(doc):
        page_number = i + 1
        if max_pages and page_number > max_pages:
            break

        pix = page.get_pixmap(dpi=300)
        image_path = os.path.join(pages_dir, f"page_{page_number}.png")
        pix.save(image_path)

        with open(image_path, "rb") as f:
            content = f.read()
        vision_image = vision.Image(content=content)
        response = client.logo_detection(image=vision_image)

        if response.error.message:
            continue

        original = Image.open(image_path)
        logos = response.logo_annotations
        if not logos:
            continue

        for j, logo in enumerate(logos):
            if logo.score < confidence_threshold:
                continue

            vertices = logo.bounding_poly.vertices
            left = min(v.x for v in vertices)
            top = min(v.y for v in vertices)
            right = max(v.x for v in vertices)
            bottom = max(v.y for v in vertices)

            if right <= left or bottom <= top:
                continue

            cropped = original.crop((left, top, right, bottom))
            emb = get_embedding(cropped)

            if is_similar(emb):
                continue

            filename = f"logo_p{page_number}_{j+1}.png"
            output_path = os.path.join(logos_dir, filename)
            cropped.save(output_path)
            embeddings.append(emb)
            saved_paths.append(output_path)

    return saved_paths[0]

@function_tool
def reset_image_cache():
    image_cache.clear()
    return