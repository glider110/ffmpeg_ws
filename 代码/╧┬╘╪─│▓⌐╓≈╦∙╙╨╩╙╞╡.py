import re
import time
import requests
import json
from DrissionPage import ChromiumPage, ChromiumOptions
from help import sign
import util


def get_all_notes_of_user(page: ChromiumPage, user_id: str):
    page.get(f'https://www.xiaohongshu.com/user/profile/{user_id}')
    local_storage = page.run_js("window.localStorage", as_expr=True)
    b1 = local_storage['b1']
    cookies = page.cookies(as_dict=True)
    a1 = cookies['a1']

    cursor = ''
    all_notes = []

    while True:
        uri = f'/api/sns/web/v1/user_posted?num=30&cursor={cursor}&user_id={user_id}&image_formats=jpg,webp,avif'
        js_res = page.run_js(f"window._webmsxyw('{uri}')", as_expr=True)
        signs = sign(a1=a1, b1=b1, x_s=js_res.get("X-s", ""), x_t=str(js_res.get("X-t", "")))
        headers = {
            'authority': 'edith.xiaohongshu.com',
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'cache-control': 'no-cache',
            'origin': 'https://www.xiaohongshu.com',
            'pragma': 'no-cache',
            'referer': 'https://www.xiaohongshu.com/',
            'sec-ch-ua': '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            "X-S": signs["x-s"],
            "X-T": signs["x-t"],
            "X-S-Common": signs["x-s-common"],
            "X-B3-Traceid": signs["x-b3-traceid"]
        }

        url = 'https://edith.xiaohongshu.com' + uri
        response = requests.get(
            url=url,
            cookies=cookies,
            headers=headers,
        )

        if response.status_code == 200:
            json_data = response.json()
            success = json_data.get('success', False)
            if success:
                data_dict = json_data.get('data', None)
                if data_dict:
                    cursor = data_dict['cursor']
                    notes = data_dict['notes']
                    all_notes.extend(notes)
                    print(f'已获取{len(all_notes)}篇笔记数据')
                    has_more = data_dict['has_more']
                    if not has_more:
                        break
                    time.sleep(2)
                else:
                    print('data_dict is None')
                    time.sleep(5)
            else:
                print('success is False')
                time.sleep(5)
        else:
            print(f'状态码错误{response.status_code}')
            time.sleep(5)
    return all_notes


def get_note_detail_info(note_id):
    headers = {
        'accept': 'application/json, text/plain, */*',
        'content-type': 'application/json;charset=UTF-8',
        'referer': 'https://www.xiaohongshu.com/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    }
    url = f"https://www.xiaohongshu.com/explore/{note_id}"
    html_content = requests.get(url, headers=headers).text
    match = re.search(r'<script>window.__INITIAL_STATE__=(.+)</script>', html_content, re.M)
    if match is None:
        return None
    info = json.loads(match.group(1).replace(':undefined', ':null'), strict=False)

    return info


def create_page():
    co = ChromiumOptions()
    page = ChromiumPage(addr_or_opts=co)
    return page


input_str = input('请输入目标博主主页链接：\n')
user_id = input_str.split('/')[-1]
page = create_page()
all_notes = get_all_notes_of_user(page, user_id)
for index, note in enumerate(all_notes):
    print(f'第{index+1}篇/共{len(all_notes)}篇')
    note_type = note['type']
    if note_type == 'video':
        note_id = note['note_id']
        note_detail_info = get_note_detail_info(note_id)
        if note_detail_info:
            video_url = note_detail_info['note']['noteDetailMap'][note_id]['note']['video']['media'][
                'stream']['h264'][0]['masterUrl']
            util.download_file_2(video_url, user_id, f'{note_id}.mp4')
            time.sleep(2)
        else:
            print(f'获取【{note_id}】失败')
    else:
        print('不是视频笔记，跳过')
page.close()
input('下载完成，按回车退出')
