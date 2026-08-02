from extractor import _extract_headings_from_paragraphs
from download import fetch_arxiv_as_json_with_fulltext

def classifier(content, new):
    print(new)
        
        
if __name__ == "__main__":
    search_query = '"large language models"'

    # Step 1: Download
    json_output = fetch_arxiv_as_json_with_fulltext(search_query, max_results=1)

    # Step 2: Extract and Classify
    if json_output:
        content, new = _extract_headings_from_paragraphs(json_output)
        classifier(content, new)
    else:
        print("Failed to retrieve data.")