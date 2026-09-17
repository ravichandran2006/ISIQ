import requests
from bs4 import BeautifulSoup

url = "https://standardsbis.bsbedge.com/BIS_Preview.aspx?id=1011_2002_reff2019"

response = requests.get(url, timeout=10)
if response.status_code == 200:
    soup = BeautifulSoup(response.text, "html.parser")
    # Find the preview container
    content_div = soup
    if content_div:
        print(content_div.get_text(separator="\n", strip=True))
else:
    print("Failed with status:", response.status_code)
