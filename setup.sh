#!/bin/bash

version="2.36.15"
file_name="saml2aws_${version}_linux_amd64.tar.gz"

echo "CLOUD-HARVEST API AWS PLUGIN SETUP"

echo "Installing saml2aws..."

wget -P /root/ "https://github.com/Versent/saml2aws/releases/download/v${version}/${file_name}"
tar -xvf "/root/${file_name}" -C /root/
mv -v /root/saml2aws /usr/local/bin/saml2aws

echo "COMPLETE"
