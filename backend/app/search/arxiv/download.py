import urllib.request
import urllib.parse

def get_data():
    command = command_gathering()
    encoded_command = urllib.parse.quote(command)
    url = f"http://export.arxiv.org/api/query?search_query=all:{encoded_command}&max_results=1"
    
    with urllib.request.urlopen(url) as in_data:
        data = in_data.read().decode("utf-8")
    
    return data

def command_gathering():
    return input("Enter the topic you want to research on: ")

data = get_data()

print(data)