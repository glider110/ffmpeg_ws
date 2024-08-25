
import xhs
import util


input_str = input('请输入笔记链接：\n')
note_id = input_str.split('/')[-1]
print(note_id)
note_detail_info = xhs.get_note_detail_info(note_id)
if note_detail_info:
    type = note_detail_info['note']['noteDetailMap'][note_id]['note']['type']
    if type == 'video':
        video_url = note_detail_info['note']['noteDetailMap'][note_id]['note']['video']['media'][
            'stream']['h264'][0]['masterUrl']
        util.download_file(video_url, 'download', f'{note_id}.mp4')
        input('下载完成，按回车退出')
    else:
        input('输入的链接不是视频类型的笔记')
else:
    input('本次下载失败，有可能是笔记链接格式错误，或者是偶发现象。请确保链接正确并重试。')







