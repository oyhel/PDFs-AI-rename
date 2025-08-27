import os
import tiktoken
from PyPDF2 import PdfReader
from openai import OpenAI
import re
import time

client = OpenAI()

max_length = 15000


def get_new_filename_from_openai(pdf_content):
    response = client.chat.completions.create(
        model="gpt-4o",
        # messages=[
        #    {"role": "system", "content": "You are a helpful assistant designed to output JSON. \
        #      You are renaming PDF files to help an accountant. Please scan the content of the pdf \
        #      and rename the files using the follwing format: <date of purchase>_<name of company that sold the product>_<what was purchased> \
        #      reply with a filename that consists only of English characters, numbers, and underscores, \
        #     and is no longer than 150 characters. Do not include characters outside of these, as the \
        #     system may crash. Do not reply in JSON format, just reply with text. The date should be in the format of YYYY-MM-DD. \
        #     Note that the product is either in Norwegian or English. If there are more than one product and you are not \
        #     able to find out what was purchased, return the date and company."},
        #    {"role": "user", "content": pdf_content}
        # ]
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

    if re.match("^[A-Za-z0-9_]$", initial_filename):
        return initial_filename if len(initial_filename) <= 100 else initial_filename[:100]
    else:
        cleaned_filename = re.sub("^[A-Za-z0-9_]$", "", initial_filename)
        return cleaned_filename if len(cleaned_filename) <= 100 else cleaned_filename[:100]


def rename_pdfs_in_directory(directory):
    pdf_contents = []
    files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
    files.sort(key=lambda x: os.path.getmtime(os.path.join(directory, x)), reverse=True)
    for filename in files:
        if filename.endswith(".pdf"):
            filepath = os.path.join(directory, filename)
            print(f"Reading file {filepath}")
            pdf_content = pdfs_to_text_string(filepath)
            print(f"CONTENT IS: {pdf_content}")
            new_file_name = get_new_filename_from_openai(pdf_content)
            if new_file_name in [f for f in os.listdir(directory) if f.endswith(".pdf")]:
                print(f"The new filename '{new_file_name}' already exists.")
                new_file_name += "_01"

            new_filepath = os.path.join(directory, new_file_name + ".pdf")
            try:
                os.rename(filepath, new_filepath)
                print(f"File renamed to {new_filepath}")
            except Exception as e:
                print(f"An error occurred while renaming the file: {e}")


def pdfs_to_text_string(filepath):
    with open(filepath, "rb") as file:
        reader = PdfReader(file)
        content = reader.pages[0].extract_text()
        if not content.strip():
            content = "Content is empty or contains only whitespace."
        encoding = tiktoken.get_encoding("cl100k_base")
        num_tokens = len(encoding.encode(content))
        if num_tokens > max_length:
            content = content_token_cut(content, num_tokens, max_length)
        return content


def content_token_cut(content, num_tokens, max_length):
    content_length = len(content)
    while num_tokens > max_length:
        ratio = num_tokens / max_length
        new_length = int(content_length * num_tokens * (90 / 100))
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
