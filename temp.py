import  pymupdf4llm

text = pymupdf4llm.to_markdown("paper.pdf")
text = text.replace("*", "")


data = {}
heading = ""
for lines in text.splitlines():
    clean_text = lines.strip()

    if not clean_text:
        continue

    if clean_text.startswith("## ") and not clean_text.startswith("###"):
        data[(clean_text[3::])] = ""
        heading = (clean_text[3::])
    else:
        if data:
            data[heading] += clean_text



print(data)