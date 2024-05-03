import os
import requests
import tarfile
import shutil


def main():
    version = "2.36.15"
    file_name = f"saml2aws_{version}_linux_amd64.tar.gz"
    download_url = f"https://github.com/Versent/saml2aws/releases/download/v{version}/{file_name}"
    download_path = "/tmp/"
    extract_path = "/tmp/"
    move_to_path = "/usr/local/bin/saml2aws"

    print("CLOUD-HARVEST API AWS PLUGIN SETUP")

    print("Installing saml2aws...")

    # Download the file
    response = requests.get(download_url)
    with open(os.path.join(download_path, file_name), 'wb') as file:
        file.write(response.content)

    # Extract the tar file
    with tarfile.open(os.path.join(download_path, file_name), 'r:gz') as tar:
        tar.extractall(path=extract_path)

    # Move the extracted file
    shutil.move(os.path.join(extract_path, 'saml2aws'), move_to_path)

    print("COMPLETE")


if __name__ == "__main__":
    main()
