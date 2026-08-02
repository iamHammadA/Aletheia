import requests

url = "http://export.arxiv.org/api/query?search_query=all:%22large+language+models%22&start=0&max_results=1"
response = requests.get(url, timeout=30)

print(f"Status Code: {response.status_code}")
print(f"Headers: {dict(response.headers)}")
print(f"Body Preview: {response.text[:500]}")