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
    # TODO: Distinguish which Docker engine has already been installed on the system,
    # if the traditional Docker engine is installed, OK; Docker Desktop is NOT SUPPORTED.
    # will use `docker context ls` to impl the check, and `docker context use` to swtich
    # Details: Docker CLI with Docker Desktop backend does not support docker bridge network,
    # see: https://docs.docker.com/desktop/networking/#there-is-no-docker0-bridge-on-the-host
    return shutil.which(cmd) is not None

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
        
        log_error("Docker installed. Please restart the host machine for docker daemon service to take effect. Then re-run ./utils/install_apollo.py")
        sys.exit(1)
    elif dependency == 'git':
        run_cmd("sudo apt-get update")
        run_cmd("sudo apt-get install -y git")

def check_and_install_dependencies():
    """Check and install missing dependencies"""
    log_info("Checking system dependencies...")
    
    # Base dependencies (required)
    base_dependencies = {
        'git': 'Git version control',
        'docker': 'Docker container platform'
    }
    
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
    
    log_success("All dependencies are available")

def main():
    log_info("Starting Apollo automation installation...")

    # Path settings
    script_dir = Path(__file__).parent.absolute()
    project_root = script_dir.parent.absolute()
    apollo_root = project_root / "BaiduApollo"

    log_info(f"Apollo directory: {apollo_root}")
    log_info(f"META²V2V directory: {project_root}")

    # Check dependencies
    check_and_install_dependencies()

    # Check user privileges
    if os.geteuid() == 0:
        sudo_user = os.environ.get("SUDO_USER")
        if sudo_user and sudo_user != 'root':
            log_error("Detect that the script is running as root through sudo, but the current login user is not root. Please run the script directly as a non-root user, or switch to the root account and run again.")
            sys.exit(1)

    # First part: install Apollo
    log_info("=== Install Baidu Apollo ===")

    # 1. Clone code
    if not apollo_root.exists():
        log_info("Cloning Apollo code...")
        # Clone the specific version of Baidu Apollo we use, which is also
        # archived in Zenodo: https://doi.org/10.5281/zenodo.17959018
        run_cmd(f"git clone -b DoppelTest https://github.com/META-V2V/BaiduApollo.git {apollo_root}")
        log_success("Code cloned successfully")
    else:
        log_warning(f"Apollo directory already exists: {apollo_root}")
        if input("Do you want to re-clone? (y/N): ").lower() == 'y':
            shutil.rmtree(apollo_root)
        # Clone the specific version of Baidu Apollo we use, which is also
        # archived in Zenodo: https://doi.org/10.5281/zenodo.17959018
            run_cmd(f"git clone -b DoppelTest https://github.com/META-V2V/BaiduApollo.git {apollo_root}")
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
    build_cmd = f"docker exec -it {container_name} /bin/bash -c 'cd /apollo && ./apollo.sh build_cpu'"
    log_info("Building may take a while, please wait...")

    returncode, _, _ = run_cmd(build_cmd, check=False)
    if returncode == 0:
        log_success("Apollo built successfully")
        
        # Stop and remove the container after successful build
        log_info("Stopping and removing the container...")
        run_cmd(f"docker stop {container_name}")
        run_cmd(f"docker rm {container_name}")
        time.sleep(3)           # wait for the container stop and remove
        volume_names = ['yolov4', 'smoke', 'faster_rcnn', 'audio']
        for volume_name in volume_names:
            run_cmd(f'docker volume rm apollo_{volume_name}_volume_{os.getenv("USER")}')
        log_success("Container stopped and removed successfully")
    else:
        log_error("Apollo build failed")
        log_info("Please manually enter the container and run: cd /apollo && ./apollo.sh build_cpu")

    # Installation completed
    log_success("=== Apollo Installation Completed ===")
    log_info("Apollo has been successfully installed and built")
    log_info("")

if __name__ == "__main__":

    main()
