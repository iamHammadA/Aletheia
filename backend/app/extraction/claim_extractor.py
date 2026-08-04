import re
import json
import nltk

with open("arxiv_papers_full.json", "r", encoding="utf-8") as f:
    data = json.load(f)



definitive_verbs_regex = re.compile(
    r"\b(?:"
    r"asserts?|asserted|asserting|"
    r"proves?|proved|proven|proving|"
    r"demonstrates?|demonstrated|demonstrating|"
    r"establishes?|established|establishing|"
    r"confirms?|confirmed|confirming|"
    r"verif(?:y|ies|ied|ying)|"
    r"substantiates?|substantiated|substantiating|"
    r"validates?|validated|validating|"
    r"concludes?|concluded|concluding|"
    r"claims?|claimed|claiming"
    r")\b",
    re.IGNORECASE
)

for article_id in data:
    article = data[article_id]
    
    for section_heading, text in article.items():
        # Insert a newline after periods/question marks so splitlines() sees individual lines
        lines = re.split(r'(?<=[.!?])\s+', text)
        
        # Your exact logic remains intact
        for lines in lines.splitlines():
            lines_clean = lines.strip()
            if not lines_clean:
                continue
                
            matches = definitive_verbs_regex.findall(lines_clean)
            if matches:
                print(f"[{article_id} -> {section_heading}]")
                print(f"Line: {lines_clean}")
                print(f"Matches: {matches}\n")
