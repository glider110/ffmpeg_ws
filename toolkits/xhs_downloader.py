'''
Author: glider
Date: 2025-09-14
FilePath: /ffmpeg_ws/toolkits/xhs_downloader.py
Version:  v0.1
Description:
    简单版小红书下载器（基于 Selenium 抓取网页资源）
    - 支持：
        1) 单条笔记下载（图片/视频）
        2) 用户主页批量下载前 N 条笔记
    - 视频 m3u8 资源通过本地 ffmpeg 合并输出 MP4
    - 需要本机安装 Chrome/Chromium；自动安装驱动（webdriver_manager）

注意：
    - 小红书页面经常变更，若选择器失效可根据当前 DOM 调整。
    - 某些资源需要登录才能访问；可关闭 headless 并手工登录后再继续。
    - 如遇防爬/签名校验，请降低速率、增加等待、或改为手动登录态下下载。
'''
from __future__ import annotations

import argparse
import json
import os
import re
import time
import subprocess
from dataclasses import dataclass
from typing import List, Optional, Tuple

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


# ------------------------ 通用工具 ------------------------

def safe_name(name: str, max_len: int = 80) -> str:
    s = re.sub(r"[\\/:*?\"<>|\n\r\t]", "_", name).strip()
    return s[:max_len] if len(s) > max_len else s


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def ffmpeg_available() -> bool:
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except FileNotFoundError:
        return False


def join_cookies(cookies: List[dict]) -> str:
    return "; ".join([f"{c['name']}={c['value']}" for c in cookies if 'name' in c and 'value' in c])


def requests_download(url: str, out_path: str, headers: Optional[dict] = None, chunk: int = 1024 * 512) -> None:
    with requests.get(url, headers=headers, stream=True, timeout=30) as r:
        r.raise_for_status()
        with open(out_path, "wb") as f:
            for part in r.iter_content(chunk_size=chunk):
                if part:
                    f.write(part)


# ------------------------ Selenium 初始化 ------------------------

def init_driver(headless: bool = True, user_agent: Optional[str] = None,
                chromedriver_path: Optional[str] = None,
                browser_binary: Optional[str] = None,
                sniff_performance: bool = False) -> webdriver.Chrome:
    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--start-maximized")
    if user_agent:
        options.add_argument(f"--user-agent={user_agent}")
    if browser_binary:
        options.binary_location = browser_binary

    # 开启性能日志以嗅探网络请求（可选）
    if sniff_performance:
        options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})

    # 优先使用本地 chromedriver，如果提供或 PATH 中可找到
    try:
        if not chromedriver_path:
            from shutil import which
            chromedriver_path = which("chromedriver")
        if chromedriver_path and os.path.exists(chromedriver_path):
            driver = webdriver.Chrome(service=Service(chromedriver_path), options=options)
        else:
            # 回退到 webdriver_manager 在线下载
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    except Exception:
        # 再次尝试 webdriver_manager（避免偶发 which 失败）
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.set_page_load_timeout(60)
    return driver


def scroll_to_bottom(driver: webdriver.Chrome, pause: float = 1.5, max_scroll: int = 10) -> None:
    last_height = driver.execute_script("return document.body.scrollHeight")
    for _ in range(max_scroll):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(pause)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height


# ------------------------ 数据结构 ------------------------

@dataclass
class NoteMedia:
    title: str
    images: List[str]
    video_url: Optional[str]
    cover: Optional[str]


# ------------------------ 解析逻辑 ------------------------

def extract_note_links_from_profile(driver: webdriver.Chrome, profile_url: str) -> List[str]:
    driver.get(profile_url)
    # 等待主内容出现（选择器可能需要根据 DOM 调整）
    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
    except Exception:
        pass

    # 加载更多内容
    scroll_to_bottom(driver, max_scroll=15)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    # 新版 XHS 主页卡片链接选择器可能为 a[href^="/explore/"] 或 data-note-id
    links = []
    for a in soup.select('a[href^="/explore/"]'):
        href = a.get('href')
        if href:
            if href.startswith("/explore/"):
                links.append("https://www.xiaohongshu.com" + href)
            elif href.startswith("http"):
                links.append(href)
    # 去重
    links = list(dict.fromkeys(links))
    return links


def _extract_from_meta(soup: BeautifulSoup) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """从 meta 标签提取 title/og:image/og:video。"""
    title = None
    title_tag = soup.find('meta', property='og:title') or soup.find('meta', attrs={'name': 'title'})
    if title_tag:
        title = title_tag.get('content')
    og_image = None
    mi = soup.find('meta', property='og:image') or soup.find('meta', attrs={'name': 'image'})
    if mi:
        og_image = mi.get('content')
    og_video = None
    mv = soup.find('meta', property='og:video') or soup.find('meta', property='og:video:url')
    if mv:
        og_video = mv.get('content')
    return title, og_image, og_video


def _extract_background_images(soup: BeautifulSoup) -> List[str]:
    urls: List[str] = []
    for el in soup.select('[style*="background-image"]'):
        style = el.get('style') or ''
        m = re.search(r'background-image\s*:\s*url\(([^)]+)\)', style, re.IGNORECASE)
        if m:
            url = m.group(1).strip('"\' )')
            if url and url not in urls:
                urls.append(url)
    return urls


def _extract_from_state_json(driver: webdriver.Chrome) -> Tuple[List[str], List[str]]:
    """尝试从 window 全局状态中解析图片/视频链接。"""
    candidates_img: List[str] = []
    candidates_vid: List[str] = []
    try:
        raw = driver.execute_script(
            "return JSON.stringify(window.__INITIAL_STATE__ || window.__REDUX_STATE__ || window.__NEXT_DATA__ || null);"
        )
        if raw:
            data = json.loads(raw)
            text = json.dumps(data, ensure_ascii=False)
            # 粗略提取 URL
            for m in re.finditer(r"https?://[^\s'\"]+\.(?:jpg|jpeg|png)(?:\?[^'\"\s]*)?", text, re.IGNORECASE):
                url = m.group(0)
                if url not in candidates_img:
                    candidates_img.append(url)
            for m in re.finditer(r"https?://[^\s'\"]+\.(?:mp4|m3u8)(?:\?[^'\"\s]*)?", text, re.IGNORECASE):
                url = m.group(0)
                if url not in candidates_vid:
                    candidates_vid.append(url)
    except Exception:
        pass
    return candidates_img, candidates_vid


def _extract_from_performance_logs(driver: webdriver.Chrome) -> Tuple[List[str], List[str]]:
    imgs: List[str] = []
    vids: List[str] = []
    try:
        logs = driver.get_log('performance')
        for entry in logs:
            try:
                msg = json.loads(entry.get('message', '{}'))
                params = msg.get('message', {}).get('params', {})
                # 关注请求相关事件
                for key in ('request', 'response'):
                    obj = params.get(key, {})
                    url = obj.get('url')
                    if not url:
                        continue
                    url_l = url.lower()
                    if any(ext in url_l for ext in ('.jpg', '.jpeg', '.png')):
                        if url not in imgs:
                            imgs.append(url)
                    if ('.m3u8' in url_l) or url_l.endswith('.mp4'):
                        if url not in vids:
                            vids.append(url)
            except Exception:
                continue
    except Exception:
        # 未开启性能日志或不支持
        pass
    return imgs, vids


def parse_note_media(driver: webdriver.Chrome, note_url: str, *, debug: bool = False) -> NoteMedia:
    driver.get(note_url)
    WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    # 滚动几次触发懒加载
    for _ in range(3):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1.2)

    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")

    # 标题（优先 meta）
    title_meta, og_img, og_video = _extract_from_meta(soup)
    title_el = soup.select_one("h1.title, h1.note-title, h1")
    title = title_meta or (title_el.get_text(strip=True) if title_el else "note")

    images: List[str] = []
    cover = None
    video_url: Optional[str] = None

    # meta 的 og:image/og:video
    if og_img:
        images.append(og_img)
        cover = cover or og_img
    if og_video:
        video_url = video_url or og_video

    # 图片：页面上通常有 img.note-image 或 data-src
    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src")
        if not src:
            continue
        # 粗略判断图片资源（域名/后缀）
        if any(ext in src.lower() for ext in [".jpg", ".jpeg", ".png", "imageView2"]):
            images.append(src)
            if not cover:
                cover = src

    # 背景图
    for u in _extract_background_images(soup):
        images.append(u)
        if not cover:
            cover = u

    # 尝试在脚本里找视频直链或 m3u8
    for script in soup.find_all("script"):
        text = script.string or script.text or ""
        # 查找常见视频链接特征（mp4/m3u8）
        m = re.search(r"https?://[^\s'\"]+\.(mp4|m3u8)(\?[^'\"\s]*)?", text)
        if m:
            video_url = m.group(0)
            break

    # 兜底：从 video/source 标签中取
    if not video_url:
        source = soup.select_one("video source[src], video[src]")
        if source:
            video_url = source.get("src")

    # 从 window 状态 JSON 中提取
    imgs2, vids2 = _extract_from_state_json(driver)
    for u in imgs2:
        if u not in images:
            images.append(u)
    if not video_url and vids2:
        video_url = vids2[0]

    # 性能日志嗅探（若开启）
    imgs3, vids3 = _extract_from_performance_logs(driver)
    for u in imgs3:
        if u not in images:
            images.append(u)
    if not video_url and vids3:
        video_url = vids3[0]

    # 去重
    images = list(dict.fromkeys(images))

    if debug:
        print(f"[DEBUG] candidates images: {len(images)}")
        if images:
            for u in images[:10]:
                print("  ", u)
        print(f"[DEBUG] candidate video: {video_url}")

    return NoteMedia(title=title or "note", images=images, video_url=video_url, cover=cover)


# ------------------------ 下载逻辑 ------------------------

def download_note(driver: webdriver.Chrome, note_url: str, output_dir: str) -> Tuple[str, List[str]]:
    media = parse_note_media(driver, note_url)
    note_name = safe_name(media.title)
    note_dir = os.path.join(output_dir, note_name)
    ensure_dir(note_dir)

    headers = {}
    cookies = driver.get_cookies()
    if cookies:
        headers["Cookie"] = join_cookies(cookies)
    # 一些资源域名可能需要 UA
    user_agent_str = (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    headers["User-Agent"] = user_agent_str
    # 加上 Referer，部分资源会校验来源
    headers["Referer"] = note_url

    saved_paths: List[str] = []

    # 可视化解析结果
    print(f"[INFO] 解析到标题: {media.title}")
    print(f"[INFO] 解析到图片数量: {len(media.images)}，视频直链: {'有' if media.video_url else '无'}")

    # 下载图片
    for idx, url in enumerate(media.images, start=1):
        ext = ".jpg"
        m = re.search(r"\.(jpg|jpeg|png)(?:\?|$)", url, re.IGNORECASE)
        if m:
            ext = "." + m.group(1).lower()
        out_path = os.path.join(note_dir, f"img_{idx:02d}{ext}")
        try:
            requests_download(url, out_path, headers=headers)
            saved_paths.append(out_path)
            print(f"[OK] 图片已保存: {out_path}")
        except Exception as e:
            print(f"[WARN] 下载图片失败: {url} -> {e}")

    # 下载视频
    if media.video_url:
        vurl = media.video_url
        if vurl.endswith(".m3u8") or ".m3u8" in vurl:
            if not ffmpeg_available():
                print("[WARN] 未检测到 ffmpeg，跳过 m3u8 视频下载：", vurl)
            else:
                out_path = os.path.join(note_dir, f"video.mp4")
                # 为 ffmpeg 传递 UA/Referer/Cookie（多个 header 用 \r\n 分隔）
                header_lines = []
                if headers.get("Cookie"):
                    header_lines.append(f"Cookie: {headers['Cookie']}")
                if headers.get("Referer"):
                    header_lines.append(f"Referer: {headers['Referer']}")
                header_args = []
                if header_lines:
                    header_args += ["-headers", "\\r\\n".join(header_lines)]
                # 单独设置 UA
                header_args += ["-user_agent", user_agent_str]
                try:
                    cmd = [
                        "ffmpeg", "-y", *header_args,
                        "-i", vurl,
                        "-c", "copy",
                        out_path,
                    ]
                    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    if proc.returncode == 0:
                        saved_paths.append(out_path)
                        print(f"[OK] 视频已保存: {out_path}")
                    else:
                        print("[WARN] ffmpeg 合并 m3u8 失败，尝试直接下载：", vurl)
                        # 直接下载 m3u8 文本不一定有意义，这里仅兜底保存索引
                        m3u8_path = os.path.join(note_dir, "video.m3u8")
                        requests_download(vurl, m3u8_path, headers=headers)
                        saved_paths.append(m3u8_path)
                        print(f"[INFO] 已保存 m3u8 索引: {m3u8_path}")
                except Exception as e:
                    print(f"[WARN] m3u8 下载异常: {e}")
        else:
            # 直链 mp4
            out_path = os.path.join(note_dir, f"video.mp4")
            try:
                requests_download(vurl, out_path, headers=headers)
                saved_paths.append(out_path)
                print(f"[OK] 视频已保存: {out_path}")
            except Exception as e:
                print(f"[WARN] 下载视频失败: {vurl} -> {e}")

    if not saved_paths:
        print("[WARN] 未下载到任何资源：可能需要登录、或页面结构/选择器已变化。建议加参数 --login-wait 并手动登录后重试。")
    else:
        print("[INFO] 下载完成，共保存文件:")
        for pth in saved_paths:
            print("  -", pth)

    return note_dir, saved_paths


def batch_download_from_profile(profile_url: str, output_dir: str, limit: int = 20, headless: bool = False,
                                chromedriver_path: Optional[str] = None,
                                browser_binary: Optional[str] = None,
                                sniff: bool = False,
                                debug: bool = False) -> None:
    driver = init_driver(headless=headless, chromedriver_path=chromedriver_path, browser_binary=browser_binary,
                         sniff_performance=sniff)
    try:
        print("[INFO] 打开主页，若需要登录请在 60 秒内完成并刷新页面…")
        driver.get(profile_url)
        time.sleep(3)
        # 留时间让用户手动登录
        if not headless:
            time.sleep(10)

        links = extract_note_links_from_profile(driver, profile_url)
        if not links:
            print("[WARN] 未获取到笔记链接，请确认是否已登录或页面结构是否变化。")
            return

        ensure_dir(output_dir)
        print(f"[INFO] 共发现 {len(links)} 条笔记，准备下载前 {limit} 条…")
        for i, link in enumerate(links[:limit], start=1):
            print(f"[INFO] ({i}/{min(limit, len(links))}) 下载: {link}")
            try:
                download_note(driver, link, output_dir)
            except Exception as e:
                print(f"[WARN] 下载失败: {link} -> {e}")
            # 适当放缓，降低触发风控概率
            time.sleep(2)
    finally:
        driver.quit()


def download_single_note(note_url: str, output_dir: str, headless: bool = False,
                         login_wait: int = 0,
                         chromedriver_path: Optional[str] = None,
                         browser_binary: Optional[str] = None,
                         sniff: bool = False,
                         debug: bool = False) -> None:
    driver = init_driver(headless=headless, chromedriver_path=chromedriver_path, browser_binary=browser_binary,
                         sniff_performance=sniff)
    try:
        ensure_dir(output_dir)
        print(f"[INFO] 下载单条笔记: {note_url}")
        # 给用户留时间登录（在可视化模式下）
        try:
            driver.get(note_url)
        except Exception:
            pass
        if not headless and login_wait > 0:
            print(f"[INFO] 请在 {login_wait} 秒内完成登录（如需要），然后无需关闭窗口，程序将继续…")
            time.sleep(login_wait)
        media = parse_note_media(driver, note_url, debug=debug)
        # 如果解析阶段未能拿到资源，download_note 内也会再次解析与尝试下载
        download_note(driver, note_url, output_dir)
    finally:
        driver.quit()


# ------------------------ CLI ------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="小红书图片/视频下载器（Selenium 版）")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--note", help="单条笔记链接，例如 https://www.xiaohongshu.com/explore/xxxxx")
    g.add_argument("--profile", help="用户主页链接，例如 https://www.xiaohongshu.com/user/profile/xxxxxx")
    p.add_argument("-o", "--output", default="./xhs_downloads", help="下载输出目录")
    p.add_argument("-n", "--limit", type=int, default=20, help="批量下载数量（主页模式）")
    p.add_argument("--headless", action="store_true", help="使用无头模式运行浏览器（默认关闭以便可手动登录）")
    p.add_argument("--login-wait", type=int, default=0, help="单条笔记模式下，为手动登录预留的等待秒数（仅非 headless 生效）")
    p.add_argument("--sniff", action="store_true", help="启用性能日志嗅探网络请求，尝试从请求中提取图片/视频链接")
    p.add_argument("--debug", action="store_true", help="打印解析阶段的候选链接，便于排查")
    p.add_argument("--chromedriver", dest="chromedriver_path", help="本地 chromedriver 路径，可避免在线下载")
    p.add_argument("--browser-binary", dest="browser_binary", help="本地 Chrome/Chromium 可执行文件路径")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    if args.note:
        download_single_note(args.note, args.output, headless=args.headless,
                             login_wait=getattr(args, "login_wait", 0),
                             sniff=getattr(args, "sniff", False),
                             debug=getattr(args, "debug", False),
                             chromedriver_path=args.chromedriver_path,
                             browser_binary=args.browser_binary)
    else:
        batch_download_from_profile(args.profile, args.output, limit=args.limit, headless=args.headless,
                                    sniff=getattr(args, "sniff", False),
                                    debug=getattr(args, "debug", False),
                                    chromedriver_path=args.chromedriver_path,
                                    browser_binary=args.browser_binary)


if __name__ == "__main__":
    main()
