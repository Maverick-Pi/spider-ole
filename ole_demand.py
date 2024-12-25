""" --------------------------------------------------------------
 @Project      : spider
 @File         : ole_demand.py
 @IDE          : PyCharm
 @Author       : Maverick Pi
 @Date         : 2024.12.22 22:54:13
 @Description  : 欧乐影院
-------------------------------------------------------------- """
import asyncio
import logging
import os
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import aiofiles
import aiohttp
import requests
import re

from bs4 import BeautifulSoup
from lxml import etree
from tqdm.asyncio import tqdm

# 设置超时以及重试
TIME_OUT = 1200     # 超时时间
RETRY_LIMIT = 100     # 最多重试 100 次
RETRY_DELAY = 5     # 重试间隔时间 5 秒

# 影视剧概览页面 URL 地址
overview_url = ''

# 欧乐影院主域名
domain = 'https://www.olehdtv.com'
# 查询页面 URL
search_url = 'https://www.olehdtv.com/index.php/vod/search.html'

# 设置请求头
headers = {
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/131.0.0.0 Safari/537.36',
    'referer': domain + '/'
}
# 设置代理
proxy = 'socks5://127.0.0.1:7897'
proxies = {
    'http': 'http://127.0.0.1:7897',
    'https': 'http://127.0.0.1:7897'
}

# 影视剧剧名
title = ''


def get_output_dir(title_name: str):
    """
    动态获取 存储路径
    :param title_name: 路径变量
    :return: 存储路径对象
    """
    return Path(f'./download_video/{title_name}/')


def get_log_dir(title_name: str):
    return get_output_dir(title_name) / 'logs'


def get_log_file_name(file_name: str):
    return f'Episode_{file_name.zfill(2)}.log'


def create_logger(name: str, log_file: Path) -> logging.Logger:
    """
    创建独立的日志记录器
    :param name: 日志记录器名称
    :param log_file: 日志文件路径
    :return: 配置好的 Logger 实例
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.ERROR)

    # 检查是否已经有处理器，避免重复添加
    if not logger.handlers:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        formatter = logging.Formatter('%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def close_logger(logger: logging.Logger):
    """
    关闭并移除指定的日志记录器的所有处理器
    :param logger: 要关闭的日志记录器
    :return: None
    """
    for handler in logger.handlers:
        handler.close()
        logger.removeHandler(handler)


def search_teleplay(url: str):
    """
    调用欧乐影院搜索接口，解析并返回结果
    :param url: 搜索页面 URL
    :return: None | 影视剧概览 URL
    """
    # 用户输入影视剧名
    key_word = input('请输入影视剧名: ')
    # 查询页面的查询参数
    search_params = {
        'wd': key_word,
        'submit': ''
    }
    with requests.get(url, params=search_params, headers=headers, proxies=proxies) as resp:
        # 使用 XPath 解析并获取查询结果
        tree = etree.HTML(resp.text)
        results = tree.xpath('/html/body/div[2]/div[1]/div/ul/li/div[2]/h4/a')
        results_len = len(results)
        if results_len == 0:
            print('什么都没有哦！请尝试其他剧目吧！')
            return None
        elif results_len == 1:
            next_url = results[0].xpath('@href')[0]
        else:
            print('查询到多个结果:')
            for idx, result in enumerate(results):
                print(idx, result.xpath('text()')[0])
            while True:
                select_num = input('请从中选择一个（编号）: ')
                if int(select_num) < 0 or int(select_num) >= results_len:
                    print('\033[33m输入不合法！请重新选择！\033[0m')
                else:
                    next_url = results[int(select_num)].xpath('@href')[0]
                    break
        return domain + next_url


def get_overview():
    """
    根据影视剧概览页面解析出剧名以及更新状态，同时解析出各集 URL 地址并返回
    :return: 集数 URL 地址列表
    """
    global title
    # 调用搜索函数，获取影视剧概览 URL
    url = search_teleplay(search_url)

    with requests.get(url, headers=headers, proxies=proxies) as resp:
        # 使用 XPath 解析并获取影视剧名和更新状态
        tree = etree.HTML(resp.text)
        title = tree.xpath('/html/body/div[2]/div[2]/div/div/div[2]/div[1]/h2/text()')[0]
        update_status = tree.xpath('/html/body/div[2]/div[2]/div/div/div[3]/ul/li[2]/span[2]/text()')
        print(f'\033[1;32m{title}: {update_status[0]}\033[0m')
        # 使用 bs4 解析并获取播放列表所有的 URL
        main_soup = BeautifulSoup(resp.text, 'html.parser')
        play_list_box = main_soup.find('div', attrs={'id': 'playlistbox'})
        # 获取播放列表的 URL 地址
        play_list = [a.get('href') for a in play_list_box.find_all('a')][:-1]

    return play_list


def user_demand():
    """
    根据用户需求选择相应集数并返回完整的集数 URL 列表
    :return: 用户需要下载的集数 URL 列表
    """
    # 获取 集数 URL 列表
    episode_list = get_overview()
    play_list = []

    while True:
        select = input(f'总共 {len(episode_list)} 集, 请选择需要下载的集数(all / n-n): ')
        if select == 'all':
            play_list = [domain + episode for episode in episode_list]
            break
        elif match := re.match(r'\d+(-\d*)?', select):
            matches = match.group().split('-')
            start_index = int(matches[0])
            if start_index < 1 or start_index > len(episode_list):
                print(f'\033[33m输入错误！请重试!\033[0m')
                continue
            try:
                end_index = int(matches[1])
                if end_index <= start_index or end_index > len(episode_list):
                    print(f'\033[33m输入错误！请重试!\033[0m')
                    continue
                play_list = [domain + episode for episode in episode_list[start_index-1:end_index]]
                break
            except IndexError:
                play_list = [domain + episode_list[start_index-1]]
                break
        else:
            print(f'\033[33m输入错误！请重试!\033[0m')

    # 创建全局日志记录目录
    get_log_dir(title).mkdir(parents=True, exist_ok=True)

    return play_list


def parse_m3u8(url: str, tag: int):
    """
    根据传入的剧集 URL 地址解析出剧集 ts 片段完整的 URL 地址并返回
    :param url: 一集剧集页面 URL 地址
    :param tag: 解析的集数标识
    :return: ts 片段 URL 列表
    """
    # 正则匹配查找 master.m3u8 URL 地址
    pattern = re.compile(r'var player_aaaa\s*=\s*{.*?"url":\s*"(?P<master_url>.*?)"')
    # 获取到 master.m3u8 URL 地址并获取视频资源 URL 前缀
    with requests.get(url, headers=headers, proxies=proxies) as resp:
        master_m3u8_url = pattern.search(resp.text, re.S).group('master_url').replace('\\', '')
        g_url_prefix = master_m3u8_url.rsplit('/', 1)[0] + '/'
    # 请求到 master.m3u8 内容并获取 真实 m3u8 地址
    with requests.get(master_m3u8_url, headers=headers, proxies=proxies) as resp:
        real_m3u8_url = g_url_prefix + resp.text.splitlines()[2]

    # ts 片段 URL 地址列表
    segment_urls = list()
    # 请求到 真实 m3u8 内容并解析出所有 ts 片段
    with requests.get(real_m3u8_url, headers=headers, proxies=proxies) as resp:
        for line in resp.text.splitlines():
            line = line.strip()
            if line.startswith('#'):
                continue
            segment_urls.append(g_url_prefix + line)

    return segment_urls, tag


async def download_segment(session: aiohttp.ClientSession, url: str, index: int, tag: int, progress_bar: tqdm):
    """
    下载 ts 片段
    :param session: 异步下载 session
    :param url: ts 片段 URL 地址
    :param index: 片段索引
    :param tag: 集数标识，用于路径生成
    :param progress_bar: 整集下载进度条
    :return: None
    """
    # 重试次数
    retries = 0

    # 创建临时文件存储目录
    temp_directory = get_output_dir(title) / str(tag)
    ts_file = f'{index}.ts'
    ts_file_path = temp_directory / ts_file
    # 如果目录不存在则创建目录
    temp_directory.mkdir(parents=True, exist_ok=True)

    # 创建日志记录器
    logger = create_logger(f'Episode_{tag}', get_log_dir(title) / get_log_file_name(str(tag)))

    while retries <= RETRY_LIMIT:
        try:
            async with session.get(url, proxy=proxy) as resp:
                resp.raise_for_status()
                async with aiofiles.open(ts_file_path, 'wb') as f:
                    while chunk := await resp.content.read(1024 * 1024 * 10):
                        await f.write(chunk)
                progress_bar.update(1)
                break
        except (aiohttp.ClientError, asyncio.TimeoutError):
            retries += 1
            if retries <= RETRY_LIMIT:
                await asyncio.sleep(RETRY_DELAY)
            else:
                logger.error(f'第 {tag} 集 片段 {index + 1} 下载失败！URL: {url}')
        except Exception as e:
            print(f'\033[31m发生错误：{e}\033[0m')
            break

    # 关闭日志记录器
    close_logger(logger)


def merge_ts_mp4(folder_path: Path, tag: int):
    """
    合并 ts 片段为一个 mp4 文件
    :param folder_path: ts 文件所在文件路径
    :param tag: 集数标识
    :return: None
    """
    # 合并后输出文件路径
    output_file = folder_path / f'Episode_{str(tag).zfill(2)}.mp4'
    # 创建一个 文件列表
    folder_path = folder_path / str(tag)
    file_list_path = folder_path / 'file_list.txt'

    with open(file_list_path, 'w', encoding='utf-8') as f:
        for ts_file in sorted(folder_path.glob('*.ts'), key=lambda x: int(x.stem)):
            f.write(f"file '{ts_file.resolve()}'\n")

    # 使用 ffmpeg 合并
    command = ['ffmpeg',
               '-f', 'concat',
               '-safe', '0',
               '-i', str(file_list_path),
               '-c', 'copy',
               str(output_file)]
    try:
        if any(folder_path.glob('*.ts')):
            print(f'\n第{str(tag).zfill(2)}集 正在合并中......')
            subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f'\033[32m第{str(tag).zfill(2)}集 文件合并完成！\033[0m')
    except subprocess.CalledProcessError as e:
        print(f'\033[31m第{str(tag).zfill(2)}集 文件合并失败！{e}\033[0m')
    finally:
        # 删除临时文件
        clear_temp(folder_path)
        print(f'\033[32m第{str(tag).zfill(2)}集 临时文件清除完毕！\033[0m')


def clear_temp(file_path: Path):
    """
    清理临时文件
    :param file_path: 临时文件目录
    :return: None
    """
    if file_path.exists() and file_path.is_dir():
        try:
            shutil.rmtree(file_path)
        except PermissionError as e:
            print(e)


def clear_log_file(file_path: Path):
    """
    如果为空则清理日志文件，否则保留
    :param file_path: 日志文件目录
    :return: None
    """
    if not file_path.exists():
        print(f'\033[31m文件目录{file_path}不存在！\033[0m')
        return False

    operation = 0

    # 删除空的日志文件
    for file in file_path.glob('*.log'):
        if file.is_file() and file.stat().st_size == 0:
            try:
                file.unlink()
                operation += 1
            except PermissionError as e:
                print(e)

    # 如果目录为空则删除目录
    if not any(file_path.iterdir()):
        try:
            shutil.rmtree(file_path)
        except PermissionError as e:
            print(e)
        print(f'\033[32m成功清除日志文件夹！其中清除日志文件 {operation} 个\033[0m')
        return True
    else:
        print(f'\033[32m日志文件夹保留！其中清除日志文件 {operation} 个')
        return True


async def assign_tasks(tag: int, urls):
    """
    创建异步任务下载一集
    :param tag: 集数标识
    :param urls: ts 完整的 URL 列表
    :return: None
    """
    # 异步请求超时设置
    timeout = aiohttp.ClientTimeout(total=TIME_OUT, connect=TIME_OUT)

    async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
        with tqdm(desc=f'{title} 第{str(tag).zfill(2)}集', total=len(urls), unit='片') as progress_bar:
            tasks = list()
            for idx, segment_url in enumerate(urls):
                tasks.append(asyncio.create_task(download_segment(session, segment_url, idx, tag, progress_bar)))
            await asyncio.gather(*tasks)


async def process_episode(episode_url, executor: ThreadPoolExecutor, title_name):
    """
    处理单集视频，包括解析、下载和合并
    :param episode_url: 单集视频 URL 地址
    :param executor: ThreadPoolExecutor 实例
    :param title_name: 标题
    :return: None
    """
    # 提取集数标识
    tag = int(episode_url.rsplit('/', 1)[1].split('.')[0])
    segment_urls, tag = parse_m3u8(episode_url, tag)

    # 下载任务
    await assign_tasks(tag, segment_urls)

    # 合并任务（交给线程池处理）
    loop = asyncio.get_running_loop()
    output_dir = get_output_dir(title_name)
    await loop.run_in_executor(executor, merge_ts_mp4, output_dir, tag)


def check_ffmpeg():
    """
    检查用户环境，FFmpeg 的可用性检测
    :return: None
    """
    if not shutil.which('ffmpeg'):
        print('FFmpeg is not found! Please ensure it is installed and accessible.')
        os.system('pause')
        exit(1)


def main():
    # 检查 FFmpeg 可用性
    check_ffmpeg()
    # 获取用户输入的完整的集数 url 列表
    episode_url_list = user_demand()

    # 创建线程池
    with ThreadPoolExecutor() as thread_executor:
        async def run_all():
            # 使用 asyncio.gather 并行处理多集视频
            tasks = [process_episode(url, thread_executor, title) for url in episode_url_list]
            await asyncio.gather(*tasks)

        asyncio.run(run_all())

    # 清理日志文件
    clear_log_file(get_log_dir(title))
    # 程序运行完后不立即关闭，而是等待用户操作
    os.system('pause')


if __name__ == '__main__':
    main()
