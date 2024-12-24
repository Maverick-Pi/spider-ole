# 爬取欧乐影院视频资源
根据用户输入的影视剧名搜寻资源并选择相应视频资源进行下载。

采用 协程 + 多进程 开发。

## 环境配置
![Python Version](https://img.shields.io/badge/Python-3.12%2B-blue.svg)
![FFmpeg Version](https://img.shields.io/badge/FFmpeg-7.0%2B-red.svg)

为了确保您能够在相同的环境中运行项目，此处提供了两种方式来配置开发环境：使用 `conda` 或 `pip`。

### 方式一：使用 Conda 环境

如果你使用的是 `conda`，可以通过以下命令创建环境：
1. 下载 `environment.yml` 文件到您的本地。
2. 运行以下命令来创建环境：
    ```bash
   conda env create -f environment.yml
    ```
3. 激活环境：
    ```bash
   conda activate <env_name>
    ```

### 方式二：使用 Pip 环境

如果你使用的是 `pip`，可以通过以下步骤来设置环境：
1. 下载 `requirements.txt` 文件到您的本地。
2. 运行以下命令来安装所有依赖包：
    ```bash
   pip install -r requirements.txt
    ```

### 还需要额外安装 [FFmpeg](https://www.ffmpeg.org/download.html#build-windows) 用于视频合并以及格式转换

![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)
