#!/bin/bash

echo "CLOUD-HARVEST AWS PLUGIN SETUP"
echo "INSTALL AWS CLI"
# https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "/root/awscliv2.zip"
unzip /root/awscliv2.zip -d /root/
/root/aws/install

which aws || echo "FAILED TO INSTALL AWS CLI TO PATH" && exit 1

echo "COMPLETE"
