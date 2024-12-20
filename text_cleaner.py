import json
import codecs
import re

def clean_text(text):
    """
    Clean text by replacing problematic characters and ensuring proper apostrophes
    """
    # Replace various types of apostrophes and quotes with standard ones
    text = text.replace('â€™', "'")
    text = text.replace('â€œ', '"')
    text = text.replace('â€', '"')
    text = text.replace('\u2019', "'")
    text = text.replace('\u2018', "'")
    text = text.replace('\u201c', '"')
    text = text.replace('\u201d', '"')
    return text

def read_json_file(file_path):
    """
    Read JSON file with proper UTF-8 encoding and clean the text
    """
    try:
        with codecs.open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # Clean the quotes in the loaded data
        if isinstance(data, list):
            for item in data:
                if 'Quote' in item:
                    item['Quote'] = clean_text(item['Quote'])
                if 'Author' in item:
                    item['Author'] = clean_text(item['Author'])
        
        return data
    except UnicodeDecodeError:
        # If UTF-8 fails, try with a different encoding
        with codecs.open(file_path, 'r', encoding='latin-1') as f:
            data = json.load(f)
            # Clean the data as above
            if isinstance(data, list):
                for item in data:
                    if 'Quote' in item:
                        item['Quote'] = clean_text(item['Quote'])
                    if 'Author' in item:
                        item['Author'] = clean_text(item['Author'])
            return data

def write_json_file(file_path, data):
    """
    Write JSON file with proper UTF-8 encoding
    """
    with codecs.open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, ensure_ascii=False, indent=4, fp=f)

# Function to clean existing JSON file
def clean_json_file(file_path):
    """
    Clean an existing JSON file and save it back
    """
    try:
        # Read the file
        data = read_json_file(file_path)
        
        # Write it back with proper encoding
        write_json_file(file_path, data)
        
        print(f"Successfully cleaned {file_path}")
        return True
    except Exception as e:
        print(f"Error cleaning file: {str(e)}")
        return False