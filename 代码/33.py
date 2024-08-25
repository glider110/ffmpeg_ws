# -*- coding: utf-8 -*-

import requests
import re
import os

# from PIL import Image


# def webp_to_jpeg(webp_path):
#     # 获取文件名和目录
#     file_dir, file_name = os.path.split(webp_path)

#     # 检查文件扩展名是否为.webp
#     if not file_name.lower().endswith(".webp"):
#         print("输入的文件不是WebP格式！")
#         return

#     # 构建JPEG保存路径
#     jpeg_path = os.path.join(file_dir, os.path.splitext(file_name)[0] + ".jpg")

#     try:
#         # 打开WebP图片
#         webp_image = Image.open(webp_path)

#         # 将WebP图片保存为JPEG格式
#         jpeg_image = webp_image.convert("RGB")
#         jpeg_image.save(jpeg_path, "JPEG")

#         print(f"成功将{file_name}转换为JPEG格式，保存为{os.path.basename(jpeg_path)}")
#         os.remove(webp_path)
#     except Exception as e:
#         print(f"转换过程中出现错误：{str(e)}")


def get_html(url):
    url = url.split("?")[0]
    headers = {
        "authority": "www.xiaohongshu.com",
        "cache-control": "max-age=0",
        "sec-ch-ua": '"Chromium";v="21", " Not;A Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "upgrade-insecure-requests": "1",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36",
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        "sec-fetch-site": "same-origin",
        "sec-fetch-mode": "navigate",
        "sec-fetch-user": "?1",
        "sec-fetch-dest": "document",
        "accept-language": "zh-CN,zh;q=0.9",
    }

    response = requests.get(url, headers=headers)

    return response.text


def json_content(html):
    rule = r"<script>window\.__INITIAL_STATE__=(.*?)</script>"
    js = re.search(rule, html, re.I)
    if js:
        content = js.group(1)
        return content
    else:
        return None


def get_img_urls(html):
    """获取图片地址"""
    urls = re.findall(r'url":"(http://[^\":\{\}\[\]]*?wm_1)"', html)
    return set(urls)


def get_video_urls(html):
    """获取视频地址"""
    urls = re.findall(r'masterUrl":"(http://[^\":\{\}\[\]]*?.mp4)"', html)
    return set(urls)


def fix_folder_name(folder_name):
    """
    去除不能作为文件夹名的字符
    """
    # 定义要替换的非法字符正则表达式
    illegal_chars_regex = r'[\\/:\*\?"<>\|]'
    correct_name = re.sub(illegal_chars_regex, "", folder_name)

    return correct_name


def get_note_title(html):
    title = re.findall(r'noteId.*?type.*?title":"(.*?)"', html)
    if title:
        return fix_folder_name(title[0])
    else:
        return "未知标题"


def download(url, save_path):
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        with open(save_path, "wb") as f:
            for chunk in response.iter_content(1024):
                f.write(chunk)
        print("下载完成！")
    else:
        print("下载失败！")


def download_img_urls(urls):
    for n, url in enumerate(urls, 1):
        print(url)
        # 设置下载目录
        save_path = f"D:/小红书下载目录/{title}"

        if not os.path.exists(save_path):
            os.makedirs(save_path)

        webp_img = os.path.join(f"{save_path}/{n}.webp")
        download(url, webp_img)
        # webp_to_jpeg(webp_img)

    os.popen(f"explorer  {os.path.realpath(save_path)}")



def download_video_urls(urls, title):
    # 在 Linux 中使用用户的主目录作为基本路径
    base_path = os.path.expanduser('~')  # 获取用户的主目录路径
    save_path = os.path.join(base_path, "小红书下载目录", title)  # 构建完整的保存路径

    for n, url in enumerate(urls, 1):
        print(url)
        if not os.path.exists(save_path):
            os.makedirs(save_path)  # 如果目录不存在，则创建

        mp4_path = os.path.join(save_path, f"{n}.mp4")  # 创建文件路径
        download(url, mp4_path)  # 下载视频到指定路径

    # 使用 xdg-open 在默认文件管理器中打开文件夹
    try:
        os.system(f"xdg-open '{save_path}'")
    except Exception as e:
        print(f"打开目录时出错：{e}")

# if __name__ == "__main__":
#     urls = [
#         "http://example.com/video1.mp4",  # 假设的视频 URL
#         "http://example.com/video2.mp4"
#     ]
#     title = "视频下载"  # 你可以根据需要修改标题
#     download_video_urls(urls, title)



if __name__ == "__main__":
    # 图片 https://www.xiaohongshu.com/explore/639aa24f000000001f001b8f
    # 视频 https://www.xiaohongshu.com/explore/64578c160000000013030eeb
    url = input("请输入笔记URL：")
    select = input("请输入数字要下载的类型：  1 图片   2 视频\n直接回车则下载图片：")
    # main(url)

    html = get_html(url)
    js = json_content(html)
    js = js.replace(r"\u002F", r"/")

    title = get_note_title(js)

    if not select.strip() or select.strip() == "1":
        all_urls = get_img_urls(js)
        print(all_urls)
        download_img_urls(all_urls)
    elif select.strip() == "2":
        all_urls = get_video_urls(js)
        print(all_urls)

        title = "视频下载"  # 你可以根据需要修改标题
        # download_video_urls(all_urls, title)

    os.system("pause")