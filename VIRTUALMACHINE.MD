# Virtual Machine for Artifact Evaluation

This virtual machine (`review.ova`) is provided for the purpose of artifact evaluation related to the paper META²V2V submission. It contains all necessary depence, source code to reproduce the main scripts with generated data mentioned in our META²V2V paper.

## File Information

- **File name**: `review.ova`

- **Size**: 32 GB

- **SHA-256**: `2065baeae3547c069eb5db46e6c022074df0b9fdcfcbeb254ab5c44cf081484d`

> [Tip] Plase use `sha256sum review.ova` verify the integrity of the file and ensure it was downloaded correctly without corruption.

- **Version**: v1.1

## Virtual Machine Information

- **OS**: Ubuntu 24.04 LTS (amd64)

- RAM: 64 GB

- Disk: 500 GB

- **Username**: vboxuser

- **Password**: <a name="password">metavv</a>

- **Default shell**: bash

- **Installed Dependences**: Python 3.12 (with required packages installed via pip), Git, and Docker

## Minimum Host Machine Requirements

- CPU: Intel Core i9 12900K (16-core)

- RAM: 96GB

> Because the virtual machine allocates 64 GB RAM from the host.

- ROM: 600GB

> Dynamic disk allocation should be enabled in VirtualBox, so the VM will grow as needed

- Host OS: Linux (amd64), Windows (x64), mac os (intel processors, apple silicon in arm64 is not supported!)

> Due to limitations of VirtualBox, GPU passthrough is not supported. As a result, the virtual machine cannot access the host machine’s dedicated GPU. Therefore, we have compiled the CPU-only version of Baidu Apollo for this virtual machine. If you wish to run the GPU-enabled version, please follow the instructions in the README.md file in our **code repository** to install and deploy the framework on a physical machine with proper GPU support.

## Quickstart

### Import the VM

- Download & install [VirtualBox](https://www.virtualbox.org/) or any OVA v2.0 compatible virtualization software.

- Load the VM file `review.ova`. E.g., in VirtualBox: `File` → `Import Appliance` → `review.ova`.

### Start the VM

1. The system will log in automatically.

> Passwordless login has been enabled, so you can access the desktop environment without entering a password. If there is any issue, such as accidentally locking the screen, you can still log in by entering the [password](#password).

2. Open the terminal from the left sidebar.

> This will launch a shell where the `.bashrc` has been preconfigured: all Python dependencies are already set up, and the working directory is automatically set to the root of the META²V2V project. **No additional** setup is required.

### Run the main scripts

Running one of the following scripts will launch a specific exploration mode. We’ve designed a simple interactive interface, just follow the prompts to begin.

1. Start the soundness violation–driven Metamorphic Testing (MT) (search-based) via:
   
```bash
python main_soundness_ga.py
```

2. Start the robustness violation–driven Metamorphic Robustness Testing (MRT) (search-based) via:

```bash
python main_robustness_ga.py
```

3. Start the random exploration (baseline) of soundness and robustness violation via:

```bash
python main_follow_random.py
```

After running META²V2V for extended period of time, you should see record file of runtime generated under `./records`.

> *Improvements*: We encapsulate the execution of each batch within a timestamped directory created at the start of the job, in order to prevent overwriting results from multiple runs for comparison.

### Replay the runtime

We also provide two types of replay modes.

1. Using the *from_json.py* script, you can specify a scenario.json and a communication.json to reproduce the runtime of a given chromosome.

```bash
python from_json.py
```

> This script uses an interactive interface that prompts you to enter the paths to your scenario.json and communication.json files. You can simply drag the files into the terminal, as we have properly handled the quotation marks at both ends of the path.

2. You can use the *replay.py* script to loop any record file infinitely, providing a convenient way to observe the runtime behavior of a scenario from the perspective of a single ADS.

```bash
python replay.py
```
> This script uses an interactive interface that prompts you to enter the paths to the record file. You can simply drag the file into the terminal, as we have properly handled the quotation marks at both ends of the path.

## Acknowledgement

Our framework builds upon the reusable artifact of **DoppelTest** [[1](#ref1)], originally published in ICSE 2023.

> Declaration: The authors of this paper have no overlap with the DoppelTest teams and declare no conflict of interest. We strictly follow the double-blind review mechanism.

## References

<a name="ref1">[1]</a> Yuqi Huai, Yuntianyi Chen, Sumaya Almanee, Tuan Ngo, Xiang Liao, Ziwen Wan, Qi Alfred Chen, and Joshua Garcia. 2023. Doppelgänger Test Generation for Revealing Bugs in Autonomous Driving Software. In Proceedings of the 45th International Conference on Software Engineering (ICSE ’23). IEEE/ACM, Melbourne, Australia, 2591–2603. https://doi.org/10.1109/ICSE48619.2023.00216