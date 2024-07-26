import requests
from bs4 import BeautifulSoup
import re
import components.urls as urls

class clientKey:
    def __init__(self):
        self.url = urls.account_url
        self.js_files = self.fetch_js_files()

    def fetch_js_files(self):
        response = requests.get(self.url)
        if response.status_code != 200:
            print(f"Failed to fetch the webpage: {response.status_code}")
            return []
        soup = BeautifulSoup(response.text, 'html.parser')
        script_tags = soup.find_all('script')
        pattern = re.compile(r'/_next/static/chunks/.*\.js')
        js_files = [tag['src'] for tag in script_tags if 'src' in tag.attrs and pattern.match(tag['src'])]
        return js_files

    def fetch_js_file_content(self, js_file_url):
        response = requests.get(self.url + js_file_url)
        if response.status_code != 200:
            print(f"Failed to fetch the JavaScript file: {response.status_code}")
        return response

    def find_client_key_function(self, js_file_content):
        pattern = re.compile(r'function\(\w+,\s*\w+,\s*\w+\)\s*\{[^}]*ClientKey:\s*\w+[^}]*\}')
        match = pattern.search(js_file_content.text)
        if match:
            return match.group()
        # print("Could not find the function where ClientKey is defined")
        return None

    def extract_client_keys(self, function_text):
        pattern = re.compile(r'let\s+s="(\d+)",\s*r="(\w+)";')
        match = pattern.search(function_text)
        if match:
            authorized_client = match.group(1)
            client_key = match.group(2)
            return {"AuthorizedClient": authorized_client, "ClientKey": client_key}
        else:
            return {"AuthorizedClient": None, "ClientKey": None}

    def get_client_keys(self):
        for js_file in self.js_files:
            js_file_content = self.fetch_js_file_content(js_file)
            if js_file_content:
                function_text = self.find_client_key_function(js_file_content)
                if function_text:
                    client_keys = self.extract_client_keys(function_text)
                    return client_keys
        print("Could not find the function where ClientKey is defined")