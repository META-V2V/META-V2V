# INSTALL

## Software Prerequisites

- Ubuntu 18.04 or later

- Python 3.12

- **Please disable or hide the GPU drivers as much as possible to prevent Apollo’s scripts from detecting any GPU drivers and the NVIDIA Container Toolkit.**

> TODO: Modify the original DoppelTest version Baidu Apollo scripts, disable GPU driver and NVIDIA Container Toolkit detection automatically.

## Install META²V2V

Install the required Python libraries using:

```bash
pip install -r requirements.txt
```
> [Tips] A good practice is to use environment management tools such as [Anaconda](https://www.anaconda.com/) to isolate the Python environment for the project.

> If you run into issues when installing Shapely library, please first run `sudo apt-get install libgeos-dev` to install its dependencies.

## Install Baidu Apollo

You can choose either the [automatic installation](#automatic-installation) method or the follow the [manual installation](#manual-installaiton).

### Automatic Installation

To simplify the installation process, we provide an automatic script [./utils/install_apollo.py](./utils/install_apollo.py). The user just need to run this script on a clean Ubuntu system which satisfies [Software Prerequisites](#software-prerequisites) to automatically download and compile the specific version of Baidu Apollo we use.

### Manual Installaiton

If you encounter any issues with the automated script above, please report them to the authors as soon as possible so we can fix the bugs in the installation script.
You can also resolve them by following the manual installation method.

0. Make sure git, Docker are installed on your machine; otherwise, please install them manually before proceeding.

    - git: `sudo apt-get update && sudo apt-get install git`

    - Docker: https://docs.docker.com/engine/install/ubuntu/

    > **[WARNING]** Please use the traditional Docker. **Do not use** [Docker Desktop for Linux](https://docs.docker.com/desktop/setup/install/linux/), because Docker Desktop does not provide a Docker bridge network [[1](#ref1)], which prevents this project from running. If you have already installed Docker Desktop, please run `docker context ls` to check which Docker engine backend your Docker CLI is using, and then use `docker context use` to switch to the traditional Docker engine backend.

    > You should manage Docker as a non-root user after the installation: https://docs.docker.com/engine/install/linux-postinstall/

1. In the **root directory** of META²V2V (`./META-V2V`), clone the specific Baidu Apollo repository branch provided by DoppelTest [[2](#ref2)]:

```bash
git clone -b DoppelTest https://github.com/YuqiHuai/BaiduApollo.git  
```

> Declaration: The authors of this paper have no overlap with the DoppelTest teams and declare no conflict of interest. We strictly follow the double-blind review mechanism.

2. In the directory of BaiduApollo (i.e. `META-V2V/BaiduApollo` by running `cd ./BaiduApollo`), create the necessary directories by running:

```bash
mkdir data data/log data/bag data/core
```

> **[WARNING]** This step is indispensable. The framework will not run correctly without it.

3. Still in the directory of BaiduApollo, run the following to pull Apollo's official Docker images:

```bash
bash ./docker/scripts/dev_start.sh -l  
```

4. In the directory of BaiduApollo, enter the development Docker container:

```bash
bash ./docker/scripts/dev_into.sh
```

> **[WARNING]** Do not close the terminal, this script puts you inside the container shell.

5. **Inside the container**, build Apollo by running:

```bash
bash apollo.sh build_cpu
```

> **[WARING]** The GPU version of Baidu Apollo contains complex deep learning models, making it impossible to reproduce our results. Please disable all GPU devices and drivers, and compile the CPU version of Baidu Apollo.

6. After building is complete, in the **host machine**, stop the container using:

```bash
docker stop apollo_dev_${USER}
docker rm apollo_dev_${USER}
docker volume rm apollo_yolov4_volume_${USER}
docker volume rm apollo_smoke_volume_${USER}
docker volume rm apollo_faster_rcnn_volume_${USER}
docker volume rm apollo_audio_volume_${USER}
```

> This container is only used for building. If not stopped, it will continue to occupy CPU and memory, which may affect META²V2V performance.

## Acknowledgement

Our framework builds upon the reusable artifact of **DoppelTest** [[2](#ref2)], originally published in ICSE 2023.

> Declaration: The authors of this paper have no overlap with the DoppelTest teams and declare no conflict of interest. We strictly follow the double-blind review mechanism.

## References

<a name="ref1">[1]</a> Docker Docs. Docker Desktop - There is no `docker0` bridge on the host. https://docs.docker.com/desktop/features/networking/networking-how-tos/#there-is-no-docker0-bridge-on-the-host

<a name="ref2">[2]</a> Yuqi Huai, Yuntianyi Chen, Sumaya Almanee, Tuan Ngo, Xiang Liao, Ziwen Wan, Qi Alfred Chen, and Joshua Garcia. 2023. Doppelgänger Test Generation for Revealing Bugs in Autonomous Driving Software. In Proceedings of the 45th International Conference on Software Engineering (ICSE ’23). IEEE/ACM, Melbourne, Australia, 2591–2603. https://doi.org/10.1109/ICSE48619.2023.00216