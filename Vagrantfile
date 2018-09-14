Vagrant.configure(2) do |config|
    config.vm.provider "virtualbox" do |v|
        v.memory = 1800
    end
    config.vm.box = "boxcutter/ubuntu1604"
    config.vm.provision "shell", inline: <<-SHELL
cat << EOF | sudo tee /etc/apt/sources.list
deb [arch=amd64] http://fr.archive.ubuntu.com/ubuntu/ xenial main
deb [arch=amd64] http://fr.archive.ubuntu.com/ubuntu/ xenial restricted
deb [arch=amd64] http://fr.archive.ubuntu.com/ubuntu/ xenial multiverse
deb [arch=amd64] http://fr.archive.ubuntu.com/ubuntu/ xenial universe
deb [arch=amd64] http://fr.archive.ubuntu.com/ubuntu/ xenial-backports main
deb [arch=amd64] http://fr.archive.ubuntu.com/ubuntu/ xenial-backports restricted
deb [arch=amd64] http://fr.archive.ubuntu.com/ubuntu/ xenial-backports multiverse
deb [arch=amd64] http://fr.archive.ubuntu.com/ubuntu/ xenial-backports universe
deb [arch=amd64] http://fr.archive.ubuntu.com/ubuntu/ xenial-updates main
deb [arch=amd64] http://fr.archive.ubuntu.com/ubuntu/ xenial-updates restricted
deb [arch=amd64] http://fr.archive.ubuntu.com/ubuntu/ xenial-updates multiverse
deb [arch=amd64] http://fr.archive.ubuntu.com/ubuntu/ xenial-updates universe
deb [arch=amd64] http://security.ubuntu.com/ubuntu xenial-security main
deb [arch=amd64] http://security.ubuntu.com/ubuntu xenial-security restricted
deb [arch=amd64] http://security.ubuntu.com/ubuntu xenial-security multiverse
deb [arch=amd64] http://security.ubuntu.com/ubuntu xenial-security universe
EOF
sudo apt-get update
sudo locale-gen fr_FR.UTF-8
sudo apt-get install -y python-pip
    SHELL
end
