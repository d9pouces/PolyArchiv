Vagrant.configure(2) do |config|
    config.vm.provider "virtualbox" do |v|
        v.memory = 1800
    end
    config.vm.box = "boxcutter/ubuntu1604"
    config.vm.provision "shell", inline: <<-SHELL
cat << EOF | sudo tee /etc/apt/sources.list
deb [arch=amd64] http://fr.archive.ubuntu.com/ubuntu/ bionic main
deb [arch=amd64] http://fr.archive.ubuntu.com/ubuntu/ bionic restricted
deb [arch=amd64] http://fr.archive.ubuntu.com/ubuntu/ bionic multiverse
deb [arch=amd64] http://fr.archive.ubuntu.com/ubuntu/ bionic universe
deb [arch=amd64] http://fr.archive.ubuntu.com/ubuntu/ bionic-backports main
deb [arch=amd64] http://fr.archive.ubuntu.com/ubuntu/ bionic-backports restricted
deb [arch=amd64] http://fr.archive.ubuntu.com/ubuntu/ bionic-backports multiverse
deb [arch=amd64] http://fr.archive.ubuntu.com/ubuntu/ bionic-backports universe
deb [arch=amd64] http://fr.archive.ubuntu.com/ubuntu/ bionic-updates main
deb [arch=amd64] http://fr.archive.ubuntu.com/ubuntu/ bionic-updates restricted
deb [arch=amd64] http://fr.archive.ubuntu.com/ubuntu/ bionic-updates multiverse
deb [arch=amd64] http://fr.archive.ubuntu.com/ubuntu/ bionic-updates universe
deb [arch=amd64] http://security.ubuntu.com/ubuntu bionic-security main
deb [arch=amd64] http://security.ubuntu.com/ubuntu bionic-security restricted
deb [arch=amd64] http://security.ubuntu.com/ubuntu bionic-security multiverse
deb [arch=amd64] http://security.ubuntu.com/ubuntu bionic-security universe
EOF
sudo apt-get update
sudo locale-gen fr_FR.UTF-8
sudo apt-get install -y python3-pip
    SHELL
end
