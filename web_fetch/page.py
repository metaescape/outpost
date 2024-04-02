import difflib
from bs4 import BeautifulSoup
import requests


def check_and_save_html_changes(url, filepath=None):
    if not url:
        return []
    # Fetching content from the URL
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")

    if not filepath:
        filepath = "/tmp/" + url.split("/")[-1]
    # Assuming the main content is under <div class="RichText"> tags, this might change based on the actual HTML structure
    try:
        content_div = soup.find("div", class_="RichText")
        content = content_div.text if content_div else ""
    except:
        return [f"{url} 抓取失败"]

    # Read the existing file content
    try:
        with open(filepath, "r", encoding="utf-8") as file:
            existing_content = file.read()
    except FileNotFoundError:
        existing_content = ""

    # Compare and save if there's a change
    if content != existing_content:
        with open(filepath, "w", encoding="utf-8") as file:
            file.write(content)
        print("Detected changes and updated the file!")

        # Display the changes
        diff = difflib.ndiff(
            existing_content.splitlines(), content.splitlines()
        )
        changes = [
            line
            for line in diff
            if line.startswith("+ ") or line.startswith("- ")
        ]
        return changes
