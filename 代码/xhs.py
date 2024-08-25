import re
import time
import requests
import json
from DrissionPage import ChromiumPage, ChromiumOptions
from help import sign
from loguru import logger


def get_creator_info(user_id: str):
    """
    通过解析网页版的用户主页HTML，获取用户个人简要信息
    PC端用户主页的网页存在window.__INITIAL_STATE__这个变量上的，解析它即可
    eg: https://www.xiaohongshu.com/user/profile/59d8cb33de5fb4696bf17217
    """
    headers = {
        'accept': 'application/json, text/plain, */*',
        'content-type': 'application/json;charset=UTF-8',
        'referer': 'https://www.xiaohongshu.com/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    }
    url = f"https://www.xiaohongshu.com/user/profile/{user_id}"
    html_content = requests.get(url, headers=headers).text
    match = re.search(r'<script>window.__INITIAL_STATE__=(.+)</script>', html_content, re.M)
    if match is None:
        return None
    info = json.loads(match.group(1).replace(':undefined', ':null'), strict=False)

    return info


def get_all_notes_of_user(page: ChromiumPage, user_id: str):
    page.get('https://www.xiaohongshu.com')
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
                    has_more = data_dict['has_more']
                    # print(has_more)
                    if not has_more:
                        break
                    time.sleep(3)
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


@logger.catch
def get_latest_notes_of_user(user_id):
    # https://www.xiaohongshu.com/user/profile/5fd59d4900000000010022d8
    headers = {
        'accept': 'application/json, text/plain, */*',
        'content-type': 'application/json;charset=UTF-8',
        'referer': 'https://www.xiaohongshu.com/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    }
    url = f"https://www.xiaohongshu.com/user/profile/{user_id}"
    html_content = requests.get(url, headers=headers).text
    # print(html_content)
    match = re.search(r'<script>window.__INITIAL_STATE__=(.+)</script>', html_content, re.M)
    if match is None:
        return None
    info = json.loads(match.group(1).replace(':undefined', ':null'), strict=False)

    return info


def get_note_detail_info(note_id):
    headers = {
        'accept': 'application/json, text/plain, */*',
        'content-type': 'application/json;charset=UTF-8',
        'referer': 'https://www.xiaohongshu.com/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    }
    url = f"https://www.xiaohongshu.com/explore/{note_id}"
    html_content = requests.get(url, headers=headers).text
    # print(html_content)
    match = re.search(r'<script>window.__INITIAL_STATE__=(.+)</script>', html_content, re.M)
    if match is None:
        return None
    info = json.loads(match.group(1).replace(':undefined', ':null'), strict=False)

    return info
    # ['note']['noteDetailMap'][note_id]['note']['video']['consumer']['originVideoKey']


def create_page():
    co = ChromiumOptions()
    # co.no_imgs()
    # co.set_local_port(9222)
    page = ChromiumPage(addr_or_opts=co)
    # page.set.auto_handle_alert()
    return page


def insert_all_notes_of_user_to_db(user_id):
    page = create_page()
    all_notes = get_all_notes_of_user(page, user_id)
    for note in all_notes:
        note_id = note['note_id']
        info = get_note_detail_info(note_id)
        if info:
            note_info = info['note']
            note.update({'note': note_info})
            print(json.dumps(note))
            sqlite.write_to_db(user_id, note)
            time.sleep(3)
        else:
            print('get_note_detail_info 失败')
    page.close()






