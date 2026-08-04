import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import requests
from bs4 import BeautifulSoup 
import  pymupdf4llm
import json

def get_data():
    from backend.app.extraction.extractor import headings_and_text_recognization , full_data
    command = command_gathering()
    encoded_command = urllib.parse.quote(command)
    max_results = 2
    url = f"http://export.arxiv.org/api/query?search_query=all:{encoded_command}&max_results={max_results}"
    
    with urllib.request.urlopen(url) as in_data:
        raw_data = in_data.read().decode("utf-8")
    
    # print(raw_data)
    xml_data = ET.fromstring(raw_data)
    # print(xml_data)
    namespace = {"atom" : "http://www.w3.org/2005/Atom"}
    
    article_url = (xml_data.findall(".//atom:entry/atom:id", namespace))
    
    pdf_links = []
    for urls in article_url:
        pdf_links.append(pdf_extractor(urls))

    print(pdf_links)
    file_name = "paper.pdf"
    for idx, links in enumerate(pdf_links):
        response = requests.get(links, stream=True)
        
        if response.status_code == 200:
            with open(file_name, "wb") as pdf_file:
                for chunk in response.iter_content(chunk_size= 1024 * 1024):
                    if chunk:
                        pdf_file.write(chunk)
        headings_and_text_recognization(idx)
    with open("arxiv_papers_full.json", "w", encoding="utf-8") as f:
        json.dump(full_data, f, indent=4, ensure_ascii=False )
    return None
    
    
def command_gathering():
    return input("Enter the topic you want to research on: ")

def pdf_extractor(urls):
    raw_data = requests.get(urls.text)
    html_data = BeautifulSoup(raw_data.text,"html.parser")
    pdf_url = html_data.find('meta', attrs={'name': 'citation_pdf_url'})['content']

    return pdf_url

data = get_data()

print(data)