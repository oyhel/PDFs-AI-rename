import os
import tiktoken
from pdf2image import convert_from_path
from openai import OpenAI
import re
import time
from PIL import Image
import io
import base64

client = OpenAI()

max_length = 15000

def get_new_filename_from_openai(png_content):
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": "Du er en hjelpsom assistent designet for å returnere JSON output. Du hjelper en regnskapsfører med å endre navn på PDF-filer som inneholder kvitteringer fra diverse kjøp. Vennligst analyser bildet av kvitteringen og endre navn på filen. Filnavnet skal være på formen <dato for kjøp>_<firma som solgte varen>_<hva som ble kjøpt>. Svar på forespørselen med et filnavn som kun inneholder bokstaver fra det engelske alfabetet, tall og understrek. Filnavnet skal ikke være lenger enn 150 tegn. Ikke inkluder tegn utover disse. Ikke svar med JSON format, svar kun med tekst. Dato skal være på formen YYYY-MM-DD. Hvis det er flere enn ett produkt på kvitteringen, velg en kategori som innebefatter flest av disse produktene. Merk at kvitteringene hovedsakelig skal være fra året 2024."
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": f"data:image/png;base64,{png_content}"
                    }
                ]
            }
        ],
        max_tokens=300
    )
    initial_filename = response.choices[0].message.content
    filename = validate_and_trim_filename(initial_filename)
    return filename

def validate_and_trim_filename(initial_filename):
    allowed_chars = r'[a-zA-Z0-9_]'
    
    if not initial_filename:
        timestamp = time.strftime('%Y%m%d%H%M%S', time.gmtime())
        return f'empty_file_{timestamp}'
    
    if re.match("^[A-Za-z0-9_]$", initial_filename):
        return initial_filename if len(initial_filename) <= 100 else initial_filename[:100]
    else:
        cleaned_filename = re.sub("[^A-Za-z0-9_]", '', initial_filename)
        return cleaned_filename if len(cleaned_filename) <= 100 else cleaned_filename[:100]

def rename_pdfs_in_directory(directory):
    files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
    files.sort(key=lambda x: os.path.getmtime(os.path.join(directory, x)), reverse=True)
    for filename in files:
        if filename.endswith(".pdf"):
            filepath = os.path.join(directory, filename)
            print(f"Processing file {filepath}")
            png_content = pdf_to_png_base64(filepath)
            new_file_name = get_new_filename_from_openai(png_content)
            if new_file_name in [f for f in os.listdir(directory) if f.endswith(".pdf")]:
                print(f"The new filename '{new_file_name}' already exists.")
                new_file_name += "_01"

            new_filepath = os.path.join(directory, new_file_name + ".pdf")
            try:
                os.rename(filepath, new_filepath)
                print(f"File renamed to {new_filepath}")
            except Exception as e:
                print(f"An error occurred while renaming the file: {e}")

def pdf_to_png_base64(filepath):
    images = convert_from_path(filepath, first_page=0, last_page=1)
    img_byte_arr = io.BytesIO()
    images[0].save(img_byte_arr, format='PNG')
    img_byte_arr = img_byte_arr.getvalue()
    return base64.b64encode(img_byte_arr).decode('utf-8')

def main():
    directory = ''  # Replace with your PDF directory path
    if directory == '':
      directory = input("Please input your path:")
    rename_pdfs_in_directory(directory)

if __name__ == "__main__":
    main()
