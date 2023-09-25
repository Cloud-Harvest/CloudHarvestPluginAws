#!/bin/bash

# installs test dependencies

# install terraform
# https://www.hashicorp.com/official-packaging-guide
apt-get update && apt-get install gpg lsb-release -y
wget -O- https://apt.releases.hashicorp.com/gpg | gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
gpg --no-default-keyring --keyring /usr/share/keyrings/hashicorp-archive-keyring.gpg --fingerprint
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | tee /etc/apt/sources.list.d/hashicorp.list
apt-get update
apt-get install terraform -y
terraform --version

# create the terraform plan
cd /src/tests/terraform
terraform init
terraform plan

