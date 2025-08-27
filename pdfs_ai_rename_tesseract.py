import os
import tiktoken
from PyPDF2 import PdfReader
from openai import OpenAI
import re
import time
from pdf2image import convert_from_path
import pytesseract

client = OpenAI()
max_length = 15000


def get_new_filename_from_openai(pdf_content):
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": "Du er en hjelpsom assistent deisgnet for å returnere JSON output. Du hjelper en en regnskapsfører med å endre navn på PDF-filer \
             som inneholder kvitteringer fra diverse kjøp. Vennligst les gjennom PDF-filen og endre navn på filen. Filnavnet skal være \
             på formen <dato for kjøp>_<firma som solgte varen>_<hva som ble kjøpt>. \
             Svar på forespørselen med et filnavn som kun inneholder bokstaver fra det engelske alfabetet, tall og understrek. \
             Filnavnet skal ikke være lenger enn 150 tegn. Ikke inkluder tegn utover disse. \
             Ikke svar med JSON format, svar kun med tekst. Dato skal være på formen YYYY-MM-DD. \
             Hvis det er flere enn ett produkt på kvitteringen, velg en kategori som innebefatter flest av disse produktene.\
             Merk at kvitteringene hovedsakelig skal være fra året 2024.",
            },
            {"role": "user", "content": pdf_content},
        ],
    )
    initial_filename = response.choices[0].message.content
    filename = validate_and_trim_filename(initial_filename)
    return filename


def validate_and_trim_filename(initial_filename):
    allowed_chars = r"[a-zA-Z0-9_]"

    if not initial_filename:
        timestamp = time.strftime("%Y%m%d%H%M%S", time.gmtime())
        return f"empty_file_{timestamp}"

    cleaned_filename = re.sub(r"[^A-Za-z0-9_]", "_", initial_filename)
    return cleaned_filename if len(cleaned_filename) <= 100 else cleaned_filename[:100]


def rename_pdfs_in_directory(directory):
    files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
    files.sort(key=lambda x: os.path.getmtime(os.path.join(directory, x)), reverse=True)

    for filename in files:
        if filename.endswith(".pdf"):
            filepath = os.path.join(directory, filename)
            print(f"Reading file {filepath}")
            pdf_content = pdfs_to_text_string(filepath)
            print(f"CONTENT IS: {pdf_content[:200]}...")  # show first 200 chars
            new_file_name = get_new_filename_from_openai(pdf_content)

            if new_file_name + ".pdf" in files:
                print(f"The new filename '{new_file_name}' already exists.")
                new_file_name += "_01"

            new_filepath = os.path.join(directory, new_file_name + ".pdf")
            try:
                os.rename(filepath, new_filepath)
                print(f"File renamed to {new_filepath}")
            except Exception as e:
                print(f"An error occurred while renaming the file: {e}")


def pdfs_to_text_string(filepath):
    """Extract text from PDF, fallback to OCR if text is empty."""
    with open(filepath, "rb") as file:
        reader = PdfReader(file)
        content = ""
        for page in reader.pages:
            text = page.extract_text()
            if text:
                content += text + "\n"

        # If no text found, fallback to OCR
        if not content.strip():
            print("No extractable text found, using OCR...")
            images = convert_from_path(filepath, dpi=300)
            ocr_texts = [pytesseract.image_to_string(img, lang="eng+nor") for img in images]
            content = "\n".join(ocr_texts)

        if not content.strip():
            content = "Content is empty or contains only whitespace."

        # Token length check
        encoding = tiktoken.get_encoding("cl100k_base")
        num_tokens = len(encoding.encode(content))
        if num_tokens > max_length:
            content = content_token_cut(content, num_tokens, max_length)

        return content


def content_token_cut(content, num_tokens, max_length):
    content_length = len(content)
    while num_tokens > max_length:
        new_length = int(content_length * 0.9)  # trim 10% iteratively
        content = content[:new_length]
        num_tokens = len(tiktoken.get_encoding("cl100k_base").encode(content))
    return content


def main():
    directory = ""  # Replace with your PDF directory path
    if directory == "":
        directory = input("Please input your path:")
    rename_pdfs_in_directory(directory)


if __name__ == "__main__":
    main()
