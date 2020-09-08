#!/bin/bash
# My first script
pip install -r requirements.txt

if [ -x "$(command -v docker)" ]; then
    echo "Docker already installed"    
else
    read -p  "Docker not found. Doy you want to install the latest version of docker now? (y/n)" choice
    case "$choice" in 
        y|Y ) echo "Installing Docker:"
            # Docker setup - commands taken from here:
            # https://docs.docker.com/engine/install/ubuntu/#install-using-the-repository
            # Uninstall old version
            sudo apt-get remove docker docker-engine docker.io containerd runc
            # 1. Update the apt package index and install packages to allow apt to use a repository over HTTPS:
            sudo apt-get update
            sudo apt-get install \
                apt-transport-https \
                ca-certificates \
                curl \
                gnupg-agent \
                software-properties-common

            # 2. Add Docker’s official GPG key:
            curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -

            # 3. Install the Docker Repository
            sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu  $(lsb_release -cs)  stable" 

            sudo apt-get update
            sudo apt-get install docker-ce
            sudo docker run hello-world;;
        n|N ) echo "You will need Docker in order to run the ikFast compilers. You can manually install docker and rerun to this script"
            exit;;
        * ) echo "Invalid! Enter 'y' or 'n'";;
    esac
fi

echo "Setting up Docker Container"
sudo chmod 666 /var/run/docker.sock
docker pull thorj/ikfast-generate-solver:firsttry
docker run -it thorj/ikfast-generate-solver:firsttry /bin/bash
exit