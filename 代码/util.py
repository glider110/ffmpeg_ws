from loguru import logger
import os
import sys
import configparser
import requests
from tqdm import tqdm
from DownloadKit import DownloadKit


def read_config():
    config = configparser.ConfigParser()
    config.read('config.ini', encoding='utf-8-sig')
    return config


# 配置打印日志的格式及保存日志文件路径
def config_log_format(log_path):
    if not os.path.exists(log_path):
        os.mkdir(log_path)
    # 按照时间命名
    log_file = os.path.join(log_path, 'log_{time}.log')
    logger.configure(handlers=[
        {
            "sink": sys.stderr,
            "format": "[{time:MM-DD HH:mm:ss}] <lvl>{message}</>",
            "colorize": True
        },
        {
            "sink": log_file,
            "format": "[{time:MM-DD HH:mm:ss}] <lvl>{message}</>",
            "colorize": False
        },
    ])


# 打印函数
def print_log(msg):
    logger.info(msg)


def download_file(file_url, folder_path, file_name):
    # 文件URL和目标文件夹
    # file_url = "http://sns-video-bd.xhscdn.com/pre_post/1040g0cg310p2gdhn6o105pflakalrgh3fqfgapg"
    # folder_path = "download"
    # file_name = "abc.mp4"

    # 创建目标文件夹
    os.makedirs(folder_path, exist_ok=True)

    # 发起GET请求下载文件
    response = requests.get(file_url, stream=True)
    if response.status_code == 200:
        # 构造目标文件路径
        file_path = os.path.join(folder_path, file_name)
        # 使用 tqdm 显示下载进度
        total_size = int(response.headers.get('content-length', 0))
        with open(file_path, 'wb') as f, tqdm(
                desc=file_name,
                total=total_size,
                unit='B',
                unit_scale=True,
                unit_divisor=1024,
                ascii=True,
                miniters=1
        ) as progress_bar:
            for data in response.iter_content(chunk_size=1024):
                f.write(data)
                progress_bar.update(len(data))
        print(f"文件已下载到 {file_path}")
    else:
        print("文件下载失败")


def download_file_2(file_url, folder_path, file_name):
    DownloadKit().download(file_url=file_url, goal_path=folder_path, rename=file_name, stream=True)



