'''
Author: glider
Date: 2024-08-04 10:56:27
LastEditTime: 2024-08-04 10:56:31
FilePath: /ffmpeg_ws/代码/11.py
Version:  v0.01
Description: 
************************************************************************
Copyright (c) 2024 by  ${git_email}, All Rights Reserved. 
************************************************************************
'''
import requests


def get_the_video_url(url):
    p = {"pageUrl": url}
    r = requests.post("https://danaqsy.com/v1/parse/dana", data=p)
    return r.json()["Data"]["Title"]+"\n", r.json()["Data"]["VideoUrls"]

def get_one_video(url, c):
    res = requests.get(url)
    # 文件写操作
    with open(f"{c}.mp4", "wb") as f:  # w：写文本 wb写字节
        f.write(res.content)
    print(f"{c}.mp4下载成功！")

if __name__ == '__main__':
    url = 'https://www.xiaohongshu.com/explore/66a58f4a000000002701eb5a?xsec_token=ABZv9SQ-uW1Uk7FmdjfIq6EkYvmE0jOeTFBo5DnYSjxgk=&xsec_source=pc_feed'
    v_title, video_url = get_the_video_url(url)
    print(v_title, video_url)
    get_one_video(video_url, "小红书视频")
