import random
import logging
import string
import os
import inspect
from shutit_module import ShutItModule

class shutit_crio(ShutItModule):


	def build(self, shutit):
		shutit.run_script('''#!/bin/bash
MODULE_NAME=shutit_crio
rm -rf $( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )/vagrant_run/*
if [[ $(command -v VBoxManage) != '' ]]
then
	while true
	do
		VBoxManage list runningvms | grep ${MODULE_NAME} | awk '{print $1}' | xargs -IXXX VBoxManage controlvm 'XXX' poweroff && VBoxManage list vms | grep shutit_crio | awk '{print $1}'  | xargs -IXXX VBoxManage unregistervm 'XXX' --delete
		# The xargs removes whitespace
		if [[ $(VBoxManage list vms | grep ${MODULE_NAME} | wc -l | xargs) -eq '0' ]]
		then
			break
		else
			ps -ef | grep virtualbox | grep ${MODULE_NAME} | awk '{print $2}' | xargs kill
			sleep 10
		fi
	done
fi
if [[ $(command -v virsh) ]] && [[ $(kvm-ok 2>&1 | command grep 'can be used') != '' ]]
then
	virsh list | grep ${MODULE_NAME} | awk '{print $1}' | xargs -n1 virsh destroy
fi
''')
		vagrant_image = shutit.cfg[self.module_id]['vagrant_image']
		vagrant_provider = shutit.cfg[self.module_id]['vagrant_provider']
		gui = shutit.cfg[self.module_id]['gui']
		memory = shutit.cfg[self.module_id]['memory']
		shutit.build['vagrant_run_dir'] = os.path.dirname(os.path.abspath(inspect.getsourcefile(lambda:0))) + '/vagrant_run'
		shutit.build['module_name'] = 'shutit_crio_' + ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(6))
		shutit.build['this_vagrant_run_dir'] = shutit.build['vagrant_run_dir'] + '/' + shutit.build['module_name']
		shutit.send(' command rm -rf ' + shutit.build['this_vagrant_run_dir'] + ' && command mkdir -p ' + shutit.build['this_vagrant_run_dir'] + ' && command cd ' + shutit.build['this_vagrant_run_dir'])
		shutit.send('command rm -rf ' + shutit.build['this_vagrant_run_dir'] + ' && command mkdir -p ' + shutit.build['this_vagrant_run_dir'] + ' && command cd ' + shutit.build['this_vagrant_run_dir'])
		if shutit.send_and_get_output('vagrant plugin list | grep landrush') == '':
			shutit.send('vagrant plugin install landrush')
		shutit.send('vagrant init ' + vagrant_image)
		shutit.send_file(shutit.build['this_vagrant_run_dir'] + '/Vagrantfile','''Vagrant.configure("2") do |config|
  config.landrush.enabled = true
  config.vm.provider "virtualbox" do |vb|
    vb.gui = ''' + gui + '''
    vb.memory = "''' + memory + '''"
  end

  config.vm.define "crio1" do |crio1|
    crio1.vm.box = ''' + '"' + vagrant_image + '"' + '''
    crio1.vm.hostname = "crio1.vagrant.test"
    config.vm.provider :virtualbox do |vb|
      vb.name = "shutit_crio_1"
    end
  end
end''')

		try:
			pw = file('secret').read().strip()
		except IOError:
			pw = ''
		if pw == '':
			shutit.log('''You can get round this manual step by creating a 'secret' with your password: 'touch secret && chmod 700 secret''',level=logging.CRITICAL)
			pw = shutit.get_env_pass()
			import time
			time.sleep(10)

		try:
			shutit.multisend('vagrant up --provider ' + shutit.cfg['shutit-library.virtualization.virtualization.virtualization']['virt_method'] + " crio1",{'assword for':pw,'assword:':pw},timeout=99999)
		except NameError:
			shutit.multisend('vagrant up crio1',{'assword for':pw,'assword:':pw},timeout=99999)

		if shutit.send_and_get_output("""vagrant status 2> /dev/null | grep -w ^crio1 | awk '{print $2}'""") != 'running':
			shutit.pause_point("machine: crio1 appears not to have come up cleanly")


		# machines is a dict of dicts containing information about each machine for you to use.
		machines = {}
		machines.update({'crio1':{'fqdn':'crio1.vagrant.test'}})
		ip = shutit.send_and_get_output('''vagrant landrush ls 2> /dev/null | grep -w ^''' + machines['crio1']['fqdn'] + ''' | awk '{print $2}' ''')
		machines.get('crio1').update({'ip':ip})


		shutit.login(command='vagrant ssh ' + sorted(machines.keys())[0],check_sudo=False)
		shutit.login(command='sudo su -',password='vagrant',check_sudo=False)
		shutit.send(r'''yum install -y \
btrfs-progs-devel \
device-mapper-devel \
git \
glib2-devel \
glibc-devel \
glibc-static \
go \
golang-github-cpuguy83-go-md2man \
gpgme-devel \
libassuan-devel \
libgpg-error-devel \
libseccomp-devel \
libselinux-devel \
ostree-devel \
pkgconfig \
runc \
skopeo-containers \
socat''')
		shutit.send('export GOPATH=~/go')
		shutit.send('export PATH=${GOPATH}/bin:${PATH}')
		#shutit.send('mkdir -p ${GOPATH}/src/github.com/opencontainers')
		#shutit.send('cd github.com/opencontainers')
		#shutit.send('git clone https://github.com/opencontainers/runc')
		#shutit.send('cd runc')
		#shutit.send('make')
		#shutit.send('make install')
		shutit.send('mkdir -p ${GOPATH}/src/github.com/kubernetes-incubator')
		shutit.send('cd ${GOPATH}/src/github.com/kubernetes-incubator')
		shutit.send('git clone https://github.com/kubernetes-incubator/cri-o')
		shutit.send('cd cri-o')
		shutit.send('make install.tools')
		shutit.send('make')
		shutit.send('make BUILDTAGS=""',note='Avoid seccomp')
		shutit.send('make install')
		shutit.send('make install.config')
		# CNI
		shutit.send('git clone https://github.com/containernetworking/plugins')
		shutit.send('cd plugins')
		shutit.send('./build.sh')
		shutit.send('mkdir -p /opt/cni/bin /etc/cni/net.d')
		shutit.send('cp bin/* /opt/cni/bin')
		shutit.send('curl https://raw.githubusercontent.com/kubernetes-incubator/cri-o/master/contrib/cni/99-loopback.conf > /etc/cni/net.d/99-loopback.conf')
		shutit.send('curl https://raw.githubusercontent.com/kubernetes-incubator/cri-o/master/contrib/cni/10-crio-bridge.conf > /etc/cni/net.d/10-crio-bridge.conf')

		#Follow this tutorial to get started with CRI-O. https://github.com/kubernetes-incubator/cri-o/blob/master/tutorial.md
		shutit.send('go get github.com/kubernetes-incubator/cri-tools/cmd/crictl')
		# CRIO DAEMON
		shutit.send(r"""sh -c 'echo "[Unit]
Description=OCI-based implementation of Kubernetes Container Runtime Interface
Documentation=https://github.com/kubernetes-incubator/cri-o

[Service]
ExecStart=/usr/local/bin/crio --log-level debug
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target" > /etc/systemd/system/crio.service'""")
		shutit.send(r"""sed -i 's/registries.*/registries = ["docker.io"/' /etc/crio/crio.conf""")
		shutit.send('systemctl daemon-reload')
		shutit.send('systemctl enable crio')
		shutit.send('systemctl start crio')
		shutit.send('crictl --runtime-endpoint /var/run/crio/crio.sock info',note='check crio is up')
		shutit.send('cd $GOPATH/src/github.com/kubernetes-incubator/cri-o')
		shutit.send('POD_ID=$(crictl runs test/testdata/sandbox_config.json)')
		shutit.send('crictl inspects --output table $POD_ID')
		shutit.send('crictl pull redis:alpine')
		shutit.send('CONTAINER_ID=$(crictl create $POD_ID /root/go/src/github.com/kubernetes-incubator/cri-o/test/testdata/sandbox_config.json)')
		shutit.send('crictl start $CONTAINER_ID')
		shutit.send('crictl inspect $CONTAINER_ID')
		shutit.pause_point('telnet 10.88.0.2 6379')

		shutit.pause_point('')
#Running with kubernetes

#You can run a local version of kubernetes with CRI-O using local-up-cluster.sh:

#Clone the kubernetes repository
#Start the CRI-O daemon (crio)
#From the kubernetes project directory, run:
#CGROUP_DRIVER=systemd \
#CONTAINER_RUNTIME=remote \
#CONTAINER_RUNTIME_ENDPOINT='/var/run/crio/crio.sock  --runtime-request-timeout=15m' \
#./hack/local-up-cluster.sh
#To run a full cluster, see the instructions.

		shutit.logout()
		shutit.logout()
		shutit.log('''Vagrantfile created in: ''' + shutit.build['this_vagrant_run_dir'],add_final_message=True,level=logging.DEBUG)
		shutit.log('''Run:

	cd ''' + shutit.build['this_vagrant_run_dir'] + ''' && vagrant status && vagrant landrush ls

To get a picture of what has been set up.''',add_final_message=True,level=logging.DEBUG)

		return True


	def get_config(self, shutit):
		shutit.get_config(self.module_id,'vagrant_image',default='centos/7')
		shutit.get_config(self.module_id,'vagrant_provider',default='virtualbox')
		shutit.get_config(self.module_id,'gui',default='false')
		shutit.get_config(self.module_id,'memory',default='1024')
		return True

	def test(self, shutit):
		return True

	def finalize(self, shutit):
		return True

	def is_installed(self, shutit):
		return False

	def start(self, shutit):
		return True

	def stop(self, shutit):
		return True

def module():
	return shutit_crio(
		'pass.shutit_crio.shutit_crio', 1124280324.0001,
		description='',
		maintainer='',
		delivery_methods=['bash'],
		depends=['shutit.tk.setup','shutit-library.virtualization.virtualization.virtualization','tk.shutit.vagrant.vagrant.vagrant']
	)
