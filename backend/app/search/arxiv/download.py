import json
import xml.etree.ElementTree as ET
import urllib.request
import requests
import os 
import time
import pdfplumber

def fetch_arxiv_as_json_with_fulltext(search_query, max_results=1):
    
    formatted_query = search_query.replace(" ", "+").replace('"',"%22")
    
    if ":" not in formatted_query.split("+")[0]:
        url = f"http://export.arxiv.org/api/query?search_query=all:{formatted_query}&start=0&max_results={max_results}"
    else:
        url = f"http://export.arxiv.org/api/query?search_query={formatted_query}&start=0&max_results={max_results}"
    
    print(f"Final URL: {url}")
    
    # Make the HTTP requests for metadata
    headers = {"User-Agent": "ArxivJsonImporter/1.0"}
    req = urllib.request.Request(url, headers=headers)
    
    try:
        with urllib.request.urlopen(req) as response:
            xml_data = response.read()
    except Exception as e:
        print(f"Error fetching data from arXiv: {e}")
        return None
    
    
    print("--- RAW API RESPONSE ---")
    print(xml_data[:500].decode('utf-8'))
    print("------------------------")
    
    # Parse the XML namespace structure
    root = ET.fromstring(xml_data)
    
    paper_list = []
    
    #Use explicit namespace for finding entries
    entries = root.findall(".//{http://www.w3.org/2005/Atom}entry")

    if not entries:
        entries = root.findall(".//{*}entry")
    
    print(f"Debug: Found {len(entries)} entries")
    
    #Define namespace URL for finding entries
    ns = {"atom":"http://www.w3.org/2005/Atom"}
    
    # iterate through each entry (paper) in the XML
    for i, entry in enumerate(entries):
        
        title_elem = entry.find("atom:title", ns)
        summary_elem = entry.find("atom:summary",ns)
        published_elem = entry.find("atom:published", ns)
        id_elem = entry.find("atom:id", ns)
        
        if title_elem is None:
            print("Warning Titlle element not foind for this entry")
            continue
        
        title = title_elem.text.strip().replace("\n"," ")
        summary = summary_elem.text.strip().replace("\n"," ") if summary_elem is not None else ""
        published = published_elem.text if published_elem is not None else ""
        paper_id_elem = id_elem.text if id_elem is not None else ""
        
        print(f"Found Title: {title[:50]}")
        
        # Extract all the authors
        authors = []
        for  author in entry.findall("atom:author", ns):
            name_elem = author.find("atom:name", ns)
            if name_elem is not None:
                authors.append(name_elem.text)
        
        # Extract direct links
        pdf_link = ""
        abs_link = ""
        for link in entry.findall("atom:link", ns):
            rel = link.attrib.get("rel")
            title_attr = link.attrib.get("title")
            href = link.attrib.get("href")
            
            if rel == "alternate":
                abs_link = href
            elif title_attr == "pdf" or "pdf" in href:
                pdf_link = href
        
        # Clean up ID
        paper_id = paper_id_elem.split("/abs/")[-1] if "/abs/" in paper_id_elem else paper_id_elem
        
        # --- New : Download PDF and Extract Full Text ---
        full_text = ""
        if pdf_link:
            try:
                print(f"Downloading PDF for {title[:50]}...")
                pdf_response = requests.get(pdf_link,headers=headers)
                if pdf_response.status_code == 200:
                    # save temporarily to extract text
                    temp_pdf = f"temp_{paper_id}.pdf"
                    with open (temp_pdf,"wb") as f:
                        f.write(pdf_response.content)
                        
                    # Extract text using pdfplumber
                    with pdfplumber.open(temp_pdf) as pdf:
                        for page in pdf.pages:
                            text = page.extract_text()
                            if text:
                                full_text += text + "\n"
                    
                    # Clean the temporary file
                    if os.path.exists(temp_pdf):
                        os.remove(temp_pdf)
                        
                    # adding the time stamp so that server gets some rest
                    time.sleep(1)
                else:
                    print(f"Failed to download PDF for {paper_id}")
            except Exception as e:
                print(f"Error processing PDF for {paper_id}: {e}")
        
        # Built the complete data object
        paper_data = {
            "id" : paper_id,
            "title" : title,
            "authors" : authors,
            "published" : published,
            "abstract" : summary,
            "full_text" : full_text,
            "Links": {
                "abstract_page" : abs_link,
                "pdf_url" : pdf_link
            }
        }
        paper_list.append(paper_data)
    

    if paper_list:
        return json.dumps(paper_list, indent=4, ensure_ascii=False)
    else:
        return None
    

        
if __name__ == "__main__":
    search_query = "large language models"
    print(f"Searching arXiv for: {search_query}...\n")
    json_output = fetch_arxiv_as_json_with_fulltext(search_query, max_results=1)

    if json_output:
        with open("arxiv_papers_full.json", "w", encoding="utf-8") as f:
            f.write(json_output)
        print("\nSuccessfully saved 'arxiv_papers_full.json' with full text!")
    else:
        print("Failed to retrieve data.")