import os
import shutil
from subprocess import run
from typing import List
from config import MT_ROOT
from apollo.container import ApolloContainer
from utils import send_push_pushover, BK_FILE_MAP

def delete_00000_files(root_dir) -> List[str]:
    """
    delete the .00000 files, i.e., the apollo cyber_record files after each batch of execution

    :param str root_dir: the root directory to be cleaned up
    :returns: the list of deleted files
    :rtype: List[str]
    """
    deleted_files = []
    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.endswith('.00000'):
                file_path = os.path.join(dirpath, filename)
                try:
                    os.remove(file_path)
                    deleted_files.append(file_path)
                except Exception as e:
                    print(f"Failed to delete {file_path}: {e}")
    return deleted_files

def compress_record_files(containers: List[ApolloContainer], timestamp: str, bk_type: str, mode: str) -> bool:
    """
    compress the record files in the record.tar.gz file in MT_ROOT directory

    :param List[ApolloContainer] containers: the containers to be used for compression
    :param str timestamp: the timestamp of the current runtime
    :param str bk_type: the type of broker to be used
    :param str mode: the mode of the main script
    :returns: True if the compression is successful, False otherwise
    :rtype: bool
    """

    root_dir = os.path.join(MT_ROOT, 'records', timestamp)

    # delete the .00000 files in the records directory of this runtime
    delete_00000_files(root_dir)

    prefix = f'{timestamp}/{BK_FILE_MAP.get(bk_type)}_{mode}'
    # compress the current root directory
    run(['tar', f'--transform=s/{timestamp}/{prefix}_{timestamp}/',
         '-czf', '../' + f'{prefix}_{timestamp}' + '.tar.gz', f'{timestamp}'], 
        cwd=os.path.join(MT_ROOT, 'records'))

    # remove the current runtime directory
    shutil.rmtree(root_dir)

    # print the size of the records_<time_stamp>.tar.gz file
    tar_path = f'{MT_ROOT}/{timestamp}.tar.gz'
    size_mb = os.path.getsize(tar_path) / 1024 / 1024
    print(f'Complete compress records, {tar_path} size: {size_mb} MB')
    hostname = os.uname().nodename
    send_push_pushover(f'{BK_FILE_MAP.get(bk_type)}_{mode} in {hostname} Done!')
    for ctn in containers:
        ctn.stop_instance()
