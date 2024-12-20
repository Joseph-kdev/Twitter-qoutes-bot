import os
from text_cleaner import clean_json_file

def main():
    """
    Clean all JSON files in the data directory
    """
    data_dir = "./data"
    
    # Clean data.json
    if os.path.exists(os.path.join(data_dir, "data.json")):
        print("Cleaning data.json...")
        clean_json_file(os.path.join(data_dir, "data.json"))
    
    # Clean tweeted.json
    if os.path.exists(os.path.join(data_dir, "tweeted.json")):
        print("Cleaning tweeted.json...")
        clean_json_file(os.path.join(data_dir, "tweeted.json"))

if __name__ == "__main__":
    main()