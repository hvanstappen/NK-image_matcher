# image_matcher.py
# BASED ON compare_images_Clip_v4.py
import os
import json
import pandas as pd
from PIL import Image
import torch
from transformers import AutoImageProcessor, AutoModel
from tqdm import tqdm
import numpy as np
import faiss
import pickle
from jinja2 import Template
import shutil
from collections import defaultdict  # Toegevoegd voor het groeperen

# -----------------------------
# CONFIG
# -----------------------------
# 1. Choose model
# model_name = "finetuning/epoch_3D_5" # ViT timm/vit_base_patch16_dinov3.lvd1689m finetuned
# model_name = "facebook/dinov2-base"
model_name = "facebook/dinov2-large"
# google/vit-base-patch16-224-in21k
# model_name = "facebook/dinov3-vitl16-pretrain-lvd1689m"
# model_name = "timm/vit_base_patch14_dinov2.lvd142m" # ViT SLOW
# model_name = "timm/vit_base_patch16_dinov3.lvd1689m" # ViT fast


# 2. Choose input image file (images to be searched, NK images)
# csv1_path = "NK_collectie/images_to_match_2D_cropped.csv" # metadata  + images of objects to be found
csv1_path = "NK_collectie/images_to_match.csv"

# 3. Choose image set (images to find match with
dir2 = "DHM/DHM_images_split_yolo_detect"  # images to match with

# -----------------------------
model_shortname = model_name.split("/")[-1]
csv1_path_shortname = csv1_path.split("/")[-1]
csv1_path_shortname = csv1_path_shortname.split(".")[0]
dir2_shortname = dir2.split("/")[-1]

config_name = model_shortname + "_" + dir2_shortname
print(f"Config: {config_name}")

# config_name = "DINO_split" # 'ViT' model name, + '_ft' for fine-tuned, + '_detect' for image set

html_name = config_name + "_" + csv1_path_shortname
print(f"HTML output: {html_name}")
# html_name = "matches_2D_orig_col" + config_name # base name output

RESULTS_PER_ITEM = 100  # max no of matches
# ITEMS_PER_PAGE = 20 # NIET MEER NODIG VOOR HTML, wel laten staan voor compatibiliteit indien nodig

device = "cuda" if torch.cuda.is_available() else "cpu"
print("Device:", device)

# -----------------------------
# Load model
# -----------------------------

processor = AutoImageProcessor.from_pretrained(model_name)
model = AutoModel.from_pretrained(model_name).to(device)
model.eval()

# -----------------------------
# Load images
# -----------------------------

df_csv1 = pd.read_csv(csv1_path)
if "reproduction.path" not in df_csv1.columns:
    raise ValueError("Column 'reproduction.path' not found in CSV")

images1 = [p for p in df_csv1["reproduction.path"].astype(str) if os.path.exists(p)]
print(f"Loaded {len(images1)} NK images from CSV")

images2 = sorted(
    os.path.join(dir2, f) for f in os.listdir(dir2)
    if f.lower().endswith(".jpg")
)
print(f"Loaded {len(images2)} DHM images")


# -----------------------------
# Compute embeddings
# -----------------------------

def compute_image_embeddings(image_paths):
    embs = []
    for path in tqdm(image_paths, desc="Embedding images"):
        try:
            img = Image.open(path).convert("RGB")
            inputs = processor(images=img, return_tensors="pt").to(device)
            with torch.no_grad():
                outputs = model(**inputs)
                emb = outputs.last_hidden_state.mean(dim=1)
            emb = emb / emb.norm(dim=-1, keepdim=True)
            embs.append(emb.cpu().numpy())
        # except Exception as e:
        #     print("Error:", e)
        #     embs.append(np.zeros((1, 768)))
        except Exception as e:
            print(f"Error processing {path}: {e}")
            continue  # or use model.config.hidden_size for dimension
    return np.vstack(embs)


# -----------------------------
# FAISS index
# -----------------------------

faiss_index_file = config_name + ".faiss"
mapping_file = config_name + ".pkl"

if os.path.exists(faiss_index_file) and os.path.exists(mapping_file):
    print("Loading FAISS index...")
    index = faiss.read_index(faiss_index_file)
    with open(mapping_file, "rb") as f:
        idx_to_path = pickle.load(f)
else:
    print("\nComputing DHM embeddings...")
    embeddings2 = compute_image_embeddings(images2).astype("float32")
    index = faiss.IndexFlatIP(embeddings2.shape[1])
    index.add(embeddings2)
    faiss.write_index(index, faiss_index_file)
    idx_to_path = {i: path for i, path in enumerate(images2)}
    with open(mapping_file, "wb") as f:
        pickle.dump(idx_to_path, f)

print("\nComputing NK embeddings...")
embeddings1 = compute_image_embeddings(images1).astype("float32")

print("Performing FAISS search...")
k = min(RESULTS_PER_ITEM, len(images2))
D, I = index.search(embeddings1, k)

# -----------------------------
# Build match data
# -----------------------------

nk_object_numbers = dict(zip(df_csv1["reproduction.path"], df_csv1.get("object_number", "")))
nk_dimensions = dict(zip(df_csv1["reproduction.path"], df_csv1.get("dimensions", "")))
nk_objectname = dict(zip(df_csv1["reproduction.path"], df_csv1.get("object_name", "")))

match_data = []
for i, img1_path in enumerate(images1):
    obj_num = str(nk_object_numbers.get(img1_path, ""))
    obj_num_base = obj_num.split("-")[0]
    obj_NK_url = "https://wo2.collectienederland.nl/doc/nk/" + obj_num_base
    dims = str(nk_dimensions.get(img1_path, ""))
    obj_name = str(nk_objectname.get(img1_path, ""))
    obj_metadata = f"{obj_name} ({dims})"

    matches = []
    for rank, idx in enumerate(I[i]):
        img2_path = idx_to_path[idx]
        sim = float(D[i][rank])
        f2 = os.path.basename(img2_path)
        base = os.path.splitext(f2)[0].split("_")[0]
        matches.append({
            "path": "../" + img2_path,
            "filename": f2,
            "base": base,
            "similarity": round(sim, 3),
            "url": f"https://www.dhm.de/datenbank/ccp/dhm_ccp_add.php?seite=6&fld_1={base}&suchen=Suchen"
        })

    match_data.append({
        "index": i,
        "source_path": "../" + img1_path,
        "source_filename": os.path.basename(img1_path),
        "object_number": obj_num,
        "obj_num_base": obj_num_base,
        "obj_metadata": obj_metadata,
        "matches": matches,
        "obj_NK_url": obj_NK_url
    })

# -----------------------------
# Generate HTML grouped by Base Number
# -----------------------------

# Create output folder based on html_name
output_folder = html_name
os.makedirs(output_folder, exist_ok=True)
print(f"Creating output folder: {output_folder}")

# Copy CSS and JS files if they exist in current directory
for file in ["styles.css", "script.js"]:
    if os.path.exists(file):
        shutil.copy(file, os.path.join(output_folder, file))
        print(f"Copied {file} to {output_folder}")

# Groepeer de data op basis van obj_num_base
grouped_data = defaultdict(list)
for item in match_data:
    base = item.get("obj_num_base", "unknown")
    grouped_data[base].append(item)

# Sorteer de bases zodat de volgorde consistent is (optioneel, maar netjes)
sorted_bases = sorted(grouped_data.keys())
total_groups = len(sorted_bases)

all_bases_json = json.dumps(sorted_bases)

with open("template.html", "r", encoding="utf-8") as f:
    template = Template(f.read())

print(f"Generating HTML files for {total_groups} unique object bases...")


# Helper functie om bestandsnaam veilig te maken (deze logic zat al in je script, nu als functie)
def get_safe_base(b_name):
    return b_name.replace("/", "_").replace("\\", "_")


# Bereken vaste waarden voor eerste en laatste pagina
first_base = get_safe_base(sorted_bases[0])
last_base = get_safe_base(sorted_bases[-1])

for i, base in enumerate(sorted_bases):
    page_data = grouped_data[base]

    # Bepaal HUIDIGE veilige bestandsnaam
    current_safe_base = get_safe_base(base)

    # Bepaal VORIGE base (indien niet de eerste pagina)
    if i > 0:
        prev_base = get_safe_base(sorted_bases[i - 1])
    else:
        prev_base = None

    # Bepaal VOLGENDE base (indien niet de laatste pagina)
    if i < total_groups - 1:
        next_base = get_safe_base(sorted_bases[i + 1])
    else:
        next_base = None

    # Render template met de nieuwe navigatie-variabelen
    html = template.render(
        items=page_data,
        current_page=i + 1,  # Voor weergave "Page 1 of 100"
        total_pages=total_groups,
        total_items=len(match_data),
        html_name=html_name,
        current_base=base,
        # NAVIGATIE VARIABELEN:
        first_base=first_base,
        last_base=last_base,
        prev_base=prev_base,
        next_base=next_base,
        all_bases_json=all_bases_json
    )

    filename = f"{html_name}_{current_safe_base}.html"
    filepath = os.path.join(output_folder, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)

    if (i + 1) % 50 == 0:
        print(f"Written {i + 1}/{total_groups}: {filepath}")

# for i, base in enumerate(sorted_bases):
#     page_data = grouped_data[base]
#
#     # Render template
#     # current_page is nu de index van het object in de lijst van unieke bases
#     html = template.render(
#         items=page_data,
#         current_page=i + 1,
#         total_pages=total_groups,
#         total_items=len(match_data),
#         html_name=html_name,
#         current_base=base  # Extra context indien nodig in template
#     )
#
#     # Filename gebaseerd op de base (verwijder eventuele schuine strepen voor veiligheid)
#     safe_base = base.replace("/", "_").replace("\\", "_")
#     filename = f"{html_name}_{safe_base}.html"
#     filepath = os.path.join(output_folder, filename)
#
#     with open(filepath, "w", encoding="utf-8") as f:
#         f.write(html)
#
#     # Print voortgang voor elke 50 bestanden om de console niet te overspoelen
#     if (i + 1) % 50 == 0:
#         print(f"Written {i + 1}/{total_groups}: {filepath}")

# ... (na de loop die alle pagina's schrijft)

# -----------------------------
# Generate Index / Landing Page
# -----------------------------
print("Generating Index page...")

# Laad de index template
if os.path.exists("index_template.html"):
    with open("index_template.html", "r", encoding="utf-8") as f:
        index_template = Template(f.read())

    # Render de index pagina
    index_html = index_template.render(
        html_name=html_name,
        first_base=first_base,    # Nodig voor de 'Start' knop
        total_groups=total_groups, # Leuk voor de statistieken
        all_bases_json=all_bases_json # Nodig voor de zoekbalk op de homepage
    )

    # Schrijf weg als index.html in de output map
    index_path = os.path.join(output_folder, "index.html")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(index_html)
    print(f"✓ Index page written: {index_path}")
else:
    print("Warning: 'index_template.html' not found. Skipping index generation.")

# EINDE SCRIPT

# Also export JSON for potential API use
json_file = os.path.join(output_folder, f"{html_name}_matches.json")
with open(json_file, "w", encoding="utf-8") as f:
    json.dump(match_data, f)

# CSV export
csv_file = os.path.join(output_folder, f"{html_name}_matches.csv")
with open(csv_file, "w", encoding="utf-8") as f:
    f.write("object_number,image1,image2,similarity\n")
    for item in match_data:
        for m in item["matches"]:
            f.write(f"{item['object_number']},{item['source_filename']},{m['filename']},{m['similarity']}\n")

print(f"✓ Done. All files written to '{output_folder}/' folder.")