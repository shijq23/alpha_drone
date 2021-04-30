# Wind River Linux Binaries on a NVIDIA Jetson Nano

This tutorial contains all the information and steps to build Wind River Linux LTS 19 on NVIDIA Jetson Nano Developer Kit B01
This tutorial is based on the blog <https://blogs.windriver.com/wind_river_blog/2020/05/nvidia-container-runtime-for-wind-river-linux/> by Pablo Rodriguez Quesada.

## Wind River Linux LTS 19 (Yocto 3.0 Zeus)

This tutorial builds Wind River Linux LTS 19.
<https://github.com/WindRiver-Labs/wrlinux-x.git>

## OpenEmbedded/Yocto BSP layer for NVIDIA Jetson Nano (meta-tegra)

To be compatible with Wind River Linux LTS 19, branch zeus-l4t-432.3.1 is used
<https://github.com/OE4T/meta-tegra.git>
This BSP supports Jetson Nano development kit (Linux4Tegra R32.3.1, JetPack 4.3)

## NVIDIA Jetson Nano 4GB Developer Kit B01

<https://developer.nvidia.com/embedded/jetson-nano-developer-kit>

## Build machine

a Ubuntu LTS 18.04 is required

## JetPack SDK 4.3

meta-tegra requires JetPack SDK 4.3.
You need first install NVIDIA SDK Manager from <https://developer.nvidia.com/embedded/downloads>.
Then run SDK Manager from /opt/nvida/sdkmanager/sdkmanager
Choose following Target Hardware:
  Jetson Nano [developer kit version]
  P3448-0000 module
  P3449-0000 carrier board
Choose following Target Operating System:
  JetPack 4.3

After SDK is installed, you should have the following folders:
Download folder $HOME/Downloads/nvidia/sdkm_downloads (~8GB)
Target HW image folder: $HOME/nvidia/nvidia_sdk (~25GB)

## TensorRT

create the subdirectory and move all of the TensorRT packages downloaded by the SDK Manager there.

$ mkdir /home/$USER/Downloads/nvidia/sdkm_downloads/NoDLA
$ cp /home/$USER/Downloads/nvidia/sdkm_downloads/libnv* /home/$USER/Downloads/nvidia/sdkm_downloads/NoDLA

## Wind River Linux LTS project

The setup program is expected to have been cloned inside of a project directory, such as:

$ mkdir $HOME/my-project
$ cd $HOME/my-project
$ git clone --branch WRLINUX_10_19_BASE https://github.com/WindRiver-Labs/wrlinux-x.git wrlinux-x

Once cloned, simply run the setup.sh (./wrlinux-x/setup.sh) to get a list of options. The setup program will construct a new git repository in the current working directory. This repository is used to manage the output of the setup program.

$ ./wrlinux-x/setup.sh
$ ./wrlinux-x/setup.sh --all-layers --dl-layers --distro wrlinux-graphics

## meta-tegra layer

[$ cd $HOME/my-project]
$ git clone --branch zeus-l4t-r32.3.1 https://github.com/madisongh/meta-tegra.git layers/meta-tegra

[$ cd $HOME/my-project]
$ . ./environment-setup-x86_64-wrlinuxsdk-linux
$ . ./oe-init-build-env

[$ cd $HOME/my-project/build]
$ bitbake-layers add-layer ../layers/meta-tegra/
$ bitbake-layers add-layer ../layers/meta-tegra/contrib
$ bitbake-layers add-layer ../layers/meta-intel
$ bitbake-layers add-layer ../layers/meta-openembedded/meta-python/
$ bitbake-layers add-layer ../layers/meta-openembedded/meta-networking/
$ bitbake-layers add-layer ../layers/meta-openembedded/meta-xfce

## config the project

[$ cd $HOME/my-project/build]
$ echo "BB_NO_NETWORK = '0'" >> conf/local.conf
$ echo 'INHERIT_DISTRO_remove = "whitelist"' >> conf/local.conf

$ echo "MACHINE='jetson-nano-qspi-sd'" >> conf/local.conf
$ echo "PREFERRED_PROVIDER_virtual/kernel = 'linux-tegra'" >> conf/local.conf

$ echo 'GCCVERSION = "7.%"' >> conf/local.conf
$ echo "require contrib/conf/include/gcc-compat.conf" >> conf/local.conf

$ echo 'IMAGE_CLASSES += "image_types_tegra"' >> conf/local.conf
$ echo 'IMAGE_FSTYPES = "tegraflash"' >> conf/local.conf

$ echo 'SECURITY_CFLAGS_pn-tini_append = " ${SECURITY_NOPIE_CFLAGS}"' >> conf/local.conf

$ echo "NVIDIA_DEVNET_MIRROR='file:///home/$USER/Downloads/nvidia/sdkm_downloads'" >> conf/local.conf
$ echo 'CUDA_BINARIES_NATIVE = "cuda-binaries-ubuntu1804-native"' >> conf/local.conf

$ echo 'IMAGE_INSTALL_append = " nvidia-docker nvidia-container-runtime cudnn tensorrt libvisionworks libvisionworks-sfm libvisionworks-tracking cuda-container-csv cudnn-container-csv tensorrt-container-csv libvisionworks-container-csv libvisionworks-sfm-container-csv libvisionworks-tracking-container-csv"' >> conf/local.conf

$ echo 'DISTRO_FEATURES_append = " ldconfig"' >> conf/local.conf

## Build the project

[$ cd $HOME/my-project/build]
$ bitbake wrlinux-image-std

## Burn the image into the SD card

[$ cd $HOME/my-project/build]
$ cd ./tmp-glibc/deploy/images/jetson-nano-qspi-sd/wrlinux-image-std-jetson-nano-qspi-sd.tegraflash.zip
$ unzip wrlinux-image-std-jetson-nano-qspi-sd-20210418032152.tegraflash.zip -d wrlinux-jetson-nano
$ cd wrlinux-jetson-nano

edit dosdcard.sh for NVIDIA Jetson Nano b00 board
MACHINE=jetson-nano-qspi-sd BOARDID=${BOARDID:-3448} FAB=${FAB:-300} ./tegra210-flash-helper.sh --sdcard -B 1048576 -s 16G -b wrlinux-image-std flash.xml.in tegra210-p3448-0000-p3449-0000-b00.dtb jetson-nano-qspi-sd.cfg 0x94000 "" boot.img wrlinux-image-std.ext4 "$@"

then run command:
$ ./dosdcard.sh
This command will create the file wrlinux-image-std.sdcard that contains the SD card image required to boot.
