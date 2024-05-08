import PyPDF2
import os
import json
from openai import OpenAI
import argparse

# please set you api key in your environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# File to keep track of perviously renamed pdfs
RENAMED_PDFS_FILE = "renamed_pdfs.json"

# function to extract pdf contents until desired number of pages or character count is reached. 
def extract_text_from_pdf(pdf_path, pages_to_extract=3, min_chars=1000):
    """Extract text from the first few pages of a PDF or until min_chars is reached."""
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        extracted_text = ""
        for page_num in range(min(pages_to_extract, len(reader.pages))):
            page_text = reader.pages[page_num].extract_text()
            extracted_text += page_text
            # Check if the cumulative extracted text has reached min_chars
            if len(extracted_text) >= min_chars:
                break
        return extracted_text[:min_chars]  # Return only up to min_chars characters

# function to send prompt to gpt-4
def get_filename_from_openai(text):
    messages = [
        {
            "role": "system",
            "content": "You are an assistant that suggests PDF filenames based on content. Suggest a filename in the format where you identify the first author's surname, the year of publication, and the title of publication. The format should be: \n '[surname year] title_of_publication.pdf' \n Include no extraneous text. 'pdf' shouldn't be used anywhere except in the file extension. Responses should only be in the forms like: \n [Ramkumar 2023] Mascara1b_CRIRES.pdf \n [Troutman 2011] βPICTORIS_rovibrational.pdf \n If there is an issue finding any of the info mentioned, with no additional text simply return: \nERROR\n"
        },
        {
            "role": "user",
            "content": f"Content:\n{text}"
        }
    ]

    client = OpenAI()
    response = client.chat.completions.create(
        model="gpt-4", 
        messages=messages
    )

    new_filename_raw = response.choices[0].message.content.strip()
    return new_filename_raw

# Creates file tracking json if one doesn't exist, otherwise loads it
def load_renamed_pdfs():
    if os.path.exists(RENAMED_PDFS_FILE):
        with open(RENAMED_PDFS_FILE, 'r') as f:
            return json.load(f)
    else:
        with open(RENAMED_PDFS_FILE, 'w') as f:
            json.dump([], f)  # Creating an empty JSON array
        return []

def save_renamed_pdfs(renamed_list):
    with open(RENAMED_PDFS_FILE, 'w') as f:
        json.dump(renamed_list, f)

def main(paper_directory : str ='./data'):
    directory = paper_directory
    
    renamed_pdfs = load_renamed_pdfs()

    for filename in os.listdir(directory):
        if filename.endswith('.pdf') and filename not in renamed_pdfs:
            text = extract_text_from_pdf(os.path.join(directory, filename))
            new_filename_raw = get_filename_from_openai(text)

            # Add condition for same name scenario (prevent duplicate rename and save)
            if filename == new_filename_raw:
                print(f"Filename: {filename} already in desired format.")
                renamed_pdfs.append(new_filename_raw)
                save_renamed_pdfs(renamed_pdfs)
                continue

            if new_filename_raw == "ERROR":
                print("Error processing file: " + filename)
                save_renamed_pdfs(renamed_pdfs)
            else:
                os.rename(os.path.join(directory, filename), os.path.join(directory, new_filename_raw))
                print("Old Filename: " + filename, "\nNew Filename: " + new_filename_raw)
                renamed_pdfs.append(new_filename_raw)
                save_renamed_pdfs(renamed_pdfs)  # Save the renamed files list after every rename

if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(
            formatter_class=argparse.ArgumentDefaultsHelpFormatter, add_help=False)
    parser.add_argument('-d',
                        '--dir',
                        type=str,
                        default='./data',
                        help='Directory where the PDFs are stored')
    parser.add_argument('-h',
                        '--help',
                        default=argparse.SUPPRESS,
                        action='help',
                        help='usage: python paper_renamer.py -d <directory> or python paper_renamer.py --dir <directory>')

    
    args = parser.parse_args()

    if args.__contains__('help'):
        parser.print_help()
        exit()


    main(args.dir)
