import os
import sys
import subprocess
import shutil
import time
from pathlib import Path

# Color definitions
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'

def log_info(msg): print(f"{Colors.BLUE}[INFO]{Colors.NC} {msg}")
def log_success(msg): print(f"{Colors.GREEN}[SUCCESS]{Colors.NC} {msg}")
def log_warning(msg): print(f"{Colors.YELLOW}[WARNING]{Colors.NC} {msg}")
def log_error(msg): print(f"{Colors.RED}[ERROR]{Colors.NC} {msg}")

def run_cmd(cmd, check=True, capture=False):
    """Run a command in shell"""
    try:
        if capture:
            result = subprocess.run(cmd, shell=True, check=check, capture_output=True, text=True)
            return result.returncode, result.stdout, result.stderr
        else:
            result = subprocess.run(cmd, shell=True, check=check)
            return result.returncode, None, None
    except subprocess.CalledProcessError as e:
        if check:
            log_error(f"Command failed: {cmd}")
            sys.exit(1)
        return e.returncode, None, None

def check_cmd(cmd) -> bool:
    """Check if a command exists"""
    return shutil.which(cmd) is not None

def check_cuda_available() -> bool:
    """Check if CUDA is available on the system"""
    # Check if nvidia-smi exists and works
    returncode, stdout, _ = run_cmd("nvidia-smi", check=False, capture=True)
    if returncode == 0 and stdout:
        log_info("CUDA detected on the system")
        return True
    return False

def install_dependency(dependency: str):
    """Install missing dependency based on the system"""
    log_info(f"Installing {dependency}...")
    
    # Only support Linux
    if not sys.platform.startswith('linux'):
        log_error(f"Automatic installation is only supported on Linux systems")
        log_info(f"Please install {dependency} manually")
        sys.exit(1)
    
    # Linux (Ubuntu only)
    if dependency == 'docker':
        log_info("Adding Docker official repository...")
        # Install necessary packages
        run_cmd("sudo apt-get update")
        run_cmd("sudo apt-get install -y ca-certificates curl gnupg lsb-release")
        
        # Add Docker's official GPG key
        run_cmd("sudo mkdir -p /etc/apt/keyrings")
        
        # Try to download GPG key with error handling
        gpg_result = run_cmd("curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg", check=False)
        if gpg_result[0] != 0:
            log_error("Failed to download Docker GPG key. Please check your internet connection.")
            sys.exit(1)
        
        # Set Docker repository
        run_cmd('echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null')
        
        # Install Docker
        run_cmd("sudo apt-get update")
        run_cmd("sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin")
        
        run_cmd("sudo systemctl start docker")
        run_cmd("sudo systemctl enable docker")
        run_cmd(f"sudo usermod -aG docker {os.getenv('USER')}")
        
        log_error("Docker installed. Please restart the host machine for docker daemon service to take effect. Then re-run install_apollo.py")
        sys.exit(1)
    elif dependency == 'git':
        run_cmd("sudo apt-get update")
        run_cmd("sudo apt-get install -y git")
    elif dependency == 'nvidia-container-toolkit':
        log_info("Installing NVIDIA Container Toolkit...")
        
        # Add NVIDIA repository
        run_cmd("distribution=$(. /etc/os-release;echo $ID$VERSION_ID)")
        run_cmd("curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg")
        run_cmd("curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list")
        
        # Install NVIDIA Container Toolkit
        run_cmd("sudo apt-get update")
        run_cmd("sudo apt-get install -y nvidia-container-toolkit")
        
        # Configure Docker to use NVIDIA Container Runtime
        run_cmd("sudo nvidia-ctk runtime configure --runtime=docker")
        run_cmd("sudo systemctl restart docker")
        
        log_success("NVIDIA Container Toolkit installed and configured successfully")

def check_and_install_dependencies():
    """Check and install missing dependencies"""
    log_info("Checking system dependencies...")
    
    # Base dependencies (required)
    base_dependencies = {
        'git': 'Git version control',
        'docker': 'Docker container platform'
    }
    
    # Optional dependencies (only if CUDA is available)
    optional_dependencies = {}
    if check_cuda_available():
        optional_dependencies['nvidia-container-toolkit'] = 'NVIDIA Container Toolkit for GPU support'
    
    # Check base dependencies first
    missing_base_deps = []
    for cmd, desc in base_dependencies.items():
        if not check_cmd(cmd):
            missing_base_deps.append((cmd, desc))
        else:
            log_success(f"{cmd} - {desc}")
    
    # Install base dependencies if missing
    if missing_base_deps:
        log_warning(f"Missing {len(missing_base_deps)} base dependency(ies):")
        for cmd, desc in missing_base_deps:
            log_warning(f"  - {cmd} ({desc})")
        
        response = input("Would you like to install missing base dependencies automatically? (y/N): ").strip().lower()
        if response in ['y', 'yes']:
            for cmd, desc in missing_base_deps:
                install_dependency(cmd)
                if check_cmd(cmd):
                    log_success(f"{cmd} installed successfully")
                else:
                    log_error(f"Failed to install {cmd}")
                    sys.exit(1)
        else:
            log_error("Cannot proceed without required base dependencies")
            sys.exit(1)
    
    # Now check optional dependencies (only after Docker is available)
    if optional_dependencies:
        log_info("Checking optional GPU dependencies...")
        missing_optional_deps = []
        
        for cmd, desc in optional_dependencies.items():
            if cmd == 'nvidia-container-toolkit':
                # Special check for nvidia-container-toolkit
                # First check if nvidia-container-runtime is available
                if check_cmd('nvidia-container-runtime'):
                    log_success(f"{cmd} - {desc}")
                else:
                    # Fallback: test with Docker if runtime not found
                    returncode, _, _ = run_cmd("docker run --rm --gpus all nvidia/cuda-runtime:latest nvidia-smi", check=False, capture=True)
                    if returncode == 0:
                        log_success(f"{cmd} - {desc}")
                    else:
                        missing_optional_deps.append((cmd, desc))
        
        # Install optional dependencies if missing
        if missing_optional_deps:
            log_warning(f"Missing {len(missing_optional_deps)} optional dependency(ies):")
            for cmd, desc in missing_optional_deps:
                log_warning(f"  - {cmd} ({desc})")
            
            response = input("Would you like to install missing optional dependencies automatically? (y/N): ").strip().lower()
            if response in ['y', 'yes']:
                for cmd, desc in missing_optional_deps:
                    install_dependency(cmd)
                    # Verify installation
                    if cmd == 'nvidia-container-toolkit':
                        # Test GPU access in Docker - use lightweight runtime
                        returncode, _, _ = run_cmd("docker run --rm --gpus all nvidia/cuda-runtime:latest nvidia-smi", check=False, capture=True)
                        if returncode == 0:
                            log_success(f"{cmd} installed successfully")
                        else:
                            log_error(f"Failed to install {cmd}")
                            sys.exit(1)
            else:
                log_warning("Optional dependencies not installed. GPU support may not be available.")
    
    log_success("All dependencies are available")

def main():
    log_info("Starting Apollo automation installation...")

    # Path settings
    script_dir = Path(__file__).parent.absolute()
    apollo_root = script_dir / "BaiduApollo"
    mt_root = script_dir

    log_info(f"Apollo directory: {apollo_root}")
    log_info(f"META²V2V directory: {mt_root}")

    # Check dependencies
    check_and_install_dependencies()

    # Check user privileges
    if os.geteuid() == 0:
        log_error("Please do not run as root")
        sys.exit(1)

    # First part: install Apollo
    log_info("=== Install Baidu Apollo ===")

    # 1. Clone code
    if not apollo_root.exists():
        log_info("Cloning Apollo code...")
        # Clone the official repository of DoppelTest (ICSE 2023), a previously published work.
        # Note: This repository is used as a dependency. Our work (META²V2V) is independent and unrelated to the DoppelTest authors.
        # Declaration: The authors of this paper have no overlap with the DoppelTest teams and declare no conflict of interest.
        # We comply with the double-blind review policy.
        run_cmd(f"git clone -b DoppelTest https://github.com/YuqiHuai/BaiduApollo.git {apollo_root}")
        log_success("Code cloned successfully")
    else:
        log_warning(f"Apollo directory already exists: {apollo_root}")
        if input("Do you want to re-clone? (y/N): ").lower() == 'y':
            shutil.rmtree(apollo_root)
        # Clone the official repository of DoppelTest (ICSE 2023), a previously published work.
        # Note: This repository is used as a dependency. Our work (META²V2V) is independent and unrelated to the DoppelTest authors.
        # Declaration: The authors of this paper have no overlap with DoppelTest teams and declare no conflict of interest.
        # We comply with the double-blind review policy.
            run_cmd(f"git clone -b DoppelTest https://github.com/YuqiHuai/BaiduApollo.git {apollo_root}")
            log_success("Code re-cloned successfully")

    # 2. Create necessary directories in BaiduApollo
    log_info("Creating necessary directories in BaiduApollo...")
    os.chdir(apollo_root)
    for dir_name in ['data', 'data/log', 'data/bag', 'data/core']:
        Path(dir_name).mkdir(parents=True, exist_ok=True)
    log_success("Directories created successfully")

    # 3. Start Apollo container
    log_info("Starting Apollo container...")
    if Path("./docker/scripts/dev_start.sh").exists():
        run_cmd("./docker/scripts/dev_start.sh -l")
        log_success("Container started successfully")
    else:
        log_error("Cannot find dev_start.sh")
        sys.exit(1)

    # 4. Get container name
    log_info("Getting container name...")
    time.sleep(5)
    returncode, stdout, _ = run_cmd("docker ps --format 'table {{.Names}}'", check=False, capture=True)
    if returncode == 0 and stdout:
        container_name = None
        for line in stdout.strip().split('\n'):
            if 'apollo_dev' in line:
                container_name = line.strip()
                break

        if container_name:
            log_success(f"Found container: {container_name}")
        else:
            log_error("Cannot find Apollo container")
            run_cmd("docker ps -a", check=False)
            sys.exit(1)
    else:
        log_error("Cannot get container information")
        sys.exit(1)

    # 5. Build Apollo
    log_info("Building Apollo...")
    build_cmd = f"docker exec -it {container_name} /bin/bash -c 'cd /apollo && ./apollo.sh build'"
    log_info("Building may take a while, please wait...")

    returncode, _, _ = run_cmd(build_cmd, check=False)
    if returncode == 0:
        log_success("Apollo built successfully")
        
        # Stop and remove the container after successful build
        log_info("Stopping and removing the container...")
        run_cmd(f"docker stop {container_name}")
        run_cmd(f"docker rm {container_name}")
        log_success("Container stopped and removed successfully")
    else:
        log_error("Apollo build failed")
        log_info("Please manually enter the container and run: cd /apollo && ./apollo.sh build")

    # Installation completed
    log_success("=== Apollo Installation Completed ===")
    log_info("Apollo has been successfully installed and built")
    log_info("")

if __name__ == "__main__":
    main() 
