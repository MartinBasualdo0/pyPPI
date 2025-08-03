import requests
from bs4 import BeautifulSoup
import re
from . import urls


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
        js_files = [tag['src']
                    for tag in script_tags if 'src' in tag.attrs and pattern.match(tag['src'])]
        return js_files

    def fetch_js_file_content(self, js_file_url):
        response = requests.get(self.url + js_file_url)
        if response.status_code != 200:
            print(f"Failed to fetch the JavaScript file: {
                  response.status_code}")
        return response

    def find_client_key_function(self, js_file_content):
        pattern = re.compile(
            r'function\(\w+,\s*\w+,\s*\w+\)\s*\{[^}]*ClientKey:\s*\w+[^}]*\}')
        match = pattern.search(js_file_content.text)
        if match:
            return match.group()
        return None

    def extract_client_keys(self, function_text):
        let_match = re.search(r'let\s+([^;]+);', function_text)
        if not let_match:
            raise ValueError(f"No let assignment found in function text: {function_text}")
        assigns = {}
        for assign in let_match.group(1).split(','):
            parts = assign.strip().split('=')
            if len(parts) == 2:
                var, val = parts
                assigns[var.strip()] = val.strip().strip('"')

        header_match = re.search(r'headers\.common=\{AuthorizedClient:([a-zA-Z_]\w*),ClientKey:([a-zA-Z_]\w*)\}', function_text)
        if header_match:
            auth_var, key_var = header_match.groups()
            authorized_client = assigns.get(auth_var)
            client_key = assigns.get(key_var)
            if authorized_client and client_key:
                return {"AuthorizedClient": authorized_client, "ClientKey": client_key}

        raise ValueError(f"Could not find 'AuthorizedClient' or 'ClientKey' in the function text. Function text: {function_text}")

    def get_client_keys(self):
        for js_file in self.js_files:
            js_file_content = self.fetch_js_file_content(js_file)
            if js_file_content:
                function_text = self.find_client_key_function(js_file_content)
                if function_text:
                    client_keys = self.extract_client_keys(function_text)
                    return client_keys
        print("Could not find the function where ClientKey is defined")
