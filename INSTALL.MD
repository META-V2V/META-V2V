# INSTALL

## Software Prerequisites

- Ubuntu 18.04 or later

- Python 3.12

- NVIDIA driver version 455.32.00 or later (Optional)

## Install *Meta²V2V*

Install the required Python libraries using:

```bash
pip install -r requirements.txt
```
> [Tips] A good practice is to use environment management tools such as [Anaconda](https://www.anaconda.com/) to isolate the Python environment for the project.

> If you run into issues when installing Shapely library, please first run `sudo apt-get install libgeos-dev` to install its dependencies.

## Install Baidu Apollo

You can choose either the [automatic installation](#automatic-installation) method or the follow the [manual installation](#manual-installaiton).

### Automatic Installation

To simplify the installation process, we provide an automatic script [install_apollo.py](install_apollo.py). The user just need to run this script on a clean Ubuntu system which satisfies [Software Prerequisites](#software-prerequisites) to automatically download and install the specific version of Baidu Apollo we use.

> The script will automatically check whether the host machine has an NVIDIA driver and whether required dependencies (e.g., git, docker, and nvidia-container-toolkit, the latter only if an `nvidia-smi` is detected) are installed, and will install any missing components accordingly.

### Manual Installaiton

If you encounter any issues with the automated script above, please report them to the authors as soon as possible so we can fix the bugs in the installation script.
You can also resolve them by following the manual installation method.

0. Make sure git, Docker, and nvidia-container-toolkit (optional, if the NVIDIA driver is available on your host machine) are installed on your machine; otherwise, please install them manually before proceeding.

    - git: `sudo apt-get update && sudo apt-get install git`

    - Docker: https://docs.docker.com/engine/install/ubuntu/

    > You should manage Docker as a non-root user after the installation: https://docs.docker.com/engine/install/linux-postinstall/

    - nvidia-container-toolkit (Optional): https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html

1. In the **root directory** of *Meta²V2V* (`./Meta-V2V`), clone the specific Baidu Apollo repository branch provided by DoppelTest [[1](#ref1)]:

```bash
git clone -b DoppelTest https://github.com/YuqiHuai/BaiduApollo.git  
```

> Declaration: The authors of this paper have no overlap with the DoppelTest teams and declare no conflict of interest. We strictly follow the double-blind review mechanism.

2. In the directory of BaiduApollo (i.e. `Meta-V2V/BaiduApollo` by running `cd ./BaiduApollo`), create the necessary directories by running:

```bash
mkdir data data/log data/bag data/core
```

> [Warning] This step is indispensable. The framework will not run correctly without it.

3. Still in the directory of BaiduApollo, run the following to pull Apollo's official Docker images:

```bash
bash ./docker/scripts/dev_start.sh -l  
```

4. In the directory of BaiduApollo, enter the development Docker container:

```bash
bash ./docker/scripts/dev_into.sh
```

> Do not close the terminal, this script puts you inside the container shell.

5. **Inside the container**, build Apollo by running:

```bash
bash apollo.sh build
```

> This will automatically start building the Apollo source code, a little bit time-consuming.

6. After building is complete, in the **host machine**, stop the container using:

```bash
docker stop apollo_dev_${USER}
```

> This container is only used for building. If not stopped, it will continue to occupy CPU and memory, which can affect *Meta²V2V* performance.

## Run the main scripts

1. Start the soundness violation–driven Metamorphic Testing (MT) (search-based) via:
   
```bash
python main_soundness_ga.py
```

2. Start the robustness violation–driven Metamorphic Robustness Testing (MRT) (search-based) via:

```bash
python main_robustness_ga.py
```

3. Start the random exploration of soundness and robustness violation via:

```bash
python main_follow_random.py
```

4. Using the [from_json](from_json.py) script, you can specify a scenario.json and a communication.json to reproduce the runtime of a given chromosome.

```bash
python from_json.py
```
> This script uses an interactive interface that prompts you to enter the paths to your scenario.json and communication.json files. You can simply drag the files into the terminal, as we have properly handled the quotation marks at both ends of the path.

After running *Meta²V2V* for extended period of time, you should see record file of scenarios generated under `./records`.

*Improvements*: We encapsulate the execution of each batch within a timestamped directory created at the start of the job, in order to prevent overwriting results from multiple runs for comparison.

5. You can use the [replay](replay.py) script to loop any record file infinitely, providing a convenient way to observe the runtime behavior of a scenario from the perspective of a single ADS.

```bash
python replay.py
```
> This script uses an interactive interface that prompts you to enter the paths to the record file. You can simply drag the file into the terminal, as we have properly handled the quotation marks at both ends of the path.

## Acknowledgement

Our framework builds upon the reusable artifact of **DoppelTest** [[1](#ref1)], originally published in ICSE 2023.

> Declaration: The authors of this paper have no overlap with the DoppelTest teams and declare no conflict of interest. We strictly follow the double-blind review mechanism.

## References

<a name="ref1">[1]</a> Yuqi Huai, Yuntianyi Chen, Sumaya Almanee, Tuan Ngo, Xiang Liao, Ziwen Wan, Qi Alfred Chen, and Joshua Garcia. 2023. Doppelgänger Test Generation for Revealing Bugs in Autonomous Driving Software. In Proceedings of the 45th International Conference on Software Engineering (ICSE ’23). IEEE/ACM, Melbourne, Australia, 2591–2603. https://doi.org/10.1109/ICSE48619.2023.00216