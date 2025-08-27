import os
import re
import time
import base64
import requests
import sys
import hashlib
import argparse
from pdf2image import convert_from_path
import tiktoken

# Use environment variable for API key
API_KEY = os.environ.get("OPENAI_API_KEY")
MAX_LENGTH = 15000

# GPT-4o pricing (as of June 2024, update as needed)
COST_PER_1K_INPUT_TOKENS = 0.005
COST_PER_1K_OUTPUT_TOKENS = 0.015


def get_new_filename_from_openai(pdf_content, verbose=False):
    """
    Uses GPT-4o to suggest a new filename from extracted PDF text.
    """
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "gpt-4o",
        "messages": [
            {
                "role": "system",
                "content": (
                    "Du er en hjelpsom assistent designet for å returnere JSON output."
                    "Du hjelper en en regnskapsfører med å endre navn på PDF-filer som inneholder kvitteringer."
                    "Filnavnet skal være på formen <YYYY-MM-DD>_<firma>_<produkt>."
                    "Svar kun med tekst, ikke JSON. Bruk kun engelske bokstaver, tall og understrek."
                    "Maks 150 tegn. Hvis flere produkter, velg en kategori som dekker flest."
                    "Kvitteringene er hovedsakelig fra inneværende år."
                ),
            },
            {"role": "user", "content": pdf_content},
        ],
    }

    start_time = time.time()
    response = requests.post(
        "https://api.openai.com/v1/chat/completions", headers=headers, json=payload
    )
    elapsed = time.time() - start_time
    response_json = response.json()
    initial_filename = response_json["choices"][0]["message"]["content"].strip()
    validated_filename = validate_and_trim_filename(initial_filename)

    # Verbose info
    if verbose:
        usage = response_json.get("usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        total_tokens = usage.get("total_tokens", 0)
        input_cost = (input_tokens / 1000) * COST_PER_1K_INPUT_TOKENS
        output_cost = (output_tokens / 1000) * COST_PER_1K_OUTPUT_TOKENS
        total_cost = input_cost + output_cost
        print(f"[VERBOSE] Filename query:")
        print(f"  Input tokens: {input_tokens}")
        print(f"  Output tokens: {output_tokens}")
        print(f"  Total tokens: {total_tokens}")
        print(f"  Time consumed: {elapsed:.2f} seconds")
        print(f"  Estimated cost: ${total_cost:.6f}")

    return validated_filename


def validate_and_trim_filename(initial_filename):
    if not initial_filename or initial_filename.lower() in ["", "unknown", "empty"]:
        return None
    cleaned_filename = re.sub(r"[^A-Za-z0-9_]", "_", initial_filename)
    return cleaned_filename[:100] if len(cleaned_filename) > 100 else cleaned_filename


def rename_pdfs_in_directory(directory, verbose=False):
    files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
    files.sort(key=lambda x: os.path.getmtime(os.path.join(directory, x)), reverse=True)

    for filename in files:
        if filename.endswith(".pdf"):
            filepath = os.path.join(directory, filename)
            print(f"Processing file: {filepath}")
            pdf_content = pdfs_to_text_string(filepath)
            print(f"CONTENT PREVIEW: {pdf_content[:200]}...")
            new_file_name = get_new_filename_from_openai(pdf_content, verbose=verbose)

            if not new_file_name:
                print(f"Skipping {filename}: no valid info for renaming.")
                continue

            if new_file_name + ".pdf" in files:
                print(f"The new filename '{new_file_name}' already exists.")
                new_file_name += "_01"

            new_filepath = os.path.join(directory, new_file_name + ".pdf")
            try:
                os.rename(filepath, new_filepath)
                print(f"Renamed file to: {new_filepath}")
            except Exception as e:
                print(f"Error renaming file: {e}")


def pdfs_to_text_string(filepath):
    """
    Converts PDF to PNG images and sends them to GPT-4o for OCR using Base64-encoded images.
    """
    images = convert_from_path(filepath, dpi=600)
    content_list = []

    for img in images:
        from io import BytesIO

        buffered = BytesIO()
        img.save(buffered, format="PNG")
        encoded_image = base64.b64encode(buffered.getvalue()).decode("utf-8")

        headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

        payload = {
            "model": "gpt-4o",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Extract all text from this image."},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{encoded_image}"},
                        },
                    ],
                }
            ],
            "max_completion_tokens": 3000,
        }

        response = requests.post(
            "https://api.openai.com/v1/chat/completions", headers=headers, json=payload
        )
        resp_json = response.json()
        ocr_text = resp_json["choices"][0]["message"]["content"].strip()
        content_list.append(ocr_text)

    content = "\n".join(content_list)
    if not content.strip():
        content = "Content is empty or contains only whitespace."

    # Token length check
    encoding = tiktoken.get_encoding("cl100k_base")
    num_tokens = len(encoding.encode(content))
    if num_tokens > MAX_LENGTH:
        content = content_token_cut(content, num_tokens, MAX_LENGTH)

    return content


def content_token_cut(content, num_tokens, max_length):
    content_length = len(content)
    while num_tokens > max_length:
        new_length = int(content_length * 0.9)
        content = content[:new_length]
        num_tokens = len(tiktoken.get_encoding("cl100k_base").encode(content))
    return content


def find_identical_files(directory):
    """
    Finds and lists pairs of identical files in the given directory, regardless of filename.
    """
    files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
    hash_dict = {}
    identical_pairs = []

    for filename in files:
        filepath = os.path.join(directory, filename)
        with open(filepath, "rb") as f:
            file_hash = hashlib.md5(f.read()).hexdigest()
        if file_hash in hash_dict:
            identical_pairs.append((hash_dict[file_hash], filename))
        else:
            hash_dict[file_hash] = filename

    if identical_pairs:
        print("Identical file pairs found:")
        for pair in identical_pairs:
            print(f"{pair[0]} <==> {pair[1]}")
    else:
        print("No identical files found.")


def main():
    parser = argparse.ArgumentParser(
        description="PDF AI Rename and Duplicate Finder",
        add_help=True,  # Enables -h/--help by default
    )
    parser.add_argument("-p", "--path", type=str, help="Path to search for PDFs")
    parser.add_argument(
        "-d", "--duplicates", action="store_true", help="Find identical files in the folder"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose mode")
    # No need to add -h manually; argparse does this automatically

    args = parser.parse_args()

    directory = args.path
    if not directory:
        directory = input("Please input your path: ")

    if args.duplicates:
        find_identical_files(directory)
    else:
        rename_pdfs_in_directory(directory, verbose=args.verbose)


if __name__ == "__main__":
    main()
