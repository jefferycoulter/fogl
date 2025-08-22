import requests

def download_gl_xml(output_filename: str="gl.xml") -> None:
    url = "https://registry.khronos.org/OpenGL/xml/gl.xml"
    try:
        response = requests.get(url)
        response.raise_for_status()
        with open(output_filename, 'wb') as file:
            file.write(response.content)
        print(f"'{output_filename}' downloaded successfully.")
    except requests.exceptions.RequestException as e:
        print(f"Error downloading '{url}': {e}")

if __name__ == "__main__":
    download_gl_xml()
