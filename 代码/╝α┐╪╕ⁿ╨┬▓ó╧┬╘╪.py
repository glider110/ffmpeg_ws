import time
from loguru import logger
import xhs
import util


def add_latest_notes_to_data_dict(latest_notes, user):
    try:
        note_list = latest_notes['user']['notes'][0]
        temp_list = []
        for note in note_list:
            note_id = note['id']
            temp_list.append(note_id)
        data_dict.update({user: temp_list})
    except KeyError:
        logger.error(f'解析用户【{user}】最新文章失败1')
    except IndexError:
        logger.error(f'解析用户【{user}】最新文章失败2')


util.config_log_format('logs')
config = util.read_config()
user_list = config.get('配置', '用户列表').split(',')
time_interval = config.getint('配置', '时间间隔')
data_dict = {}

while True:
    for user in user_list:
        latest_notes = xhs.get_latest_notes_of_user(user)
        if latest_notes is None:
            logger.error(f'获取用户【{user}】最新文章失败')
            time.sleep(5)
            break
        if user not in data_dict:
            logger.info(f'初始化【{user}】')
            add_latest_notes_to_data_dict(latest_notes, user)
            time.sleep(5)
        else:
            note_list = latest_notes['user']['notes'][0]
            for note in note_list:
                note_id = note['id']
                if note_id not in data_dict[user]:
                    data_dict[user].append(note_id)
                    note_type = note['noteCard']['type']
                    if note_type == 'video':
                        note_detail_info = xhs.get_note_detail_info(note_id)
                        if note_detail_info:
                            video_url = note_detail_info['note']['noteDetailMap'][note_id]['note']['video']['media'][
                                'stream']['h264'][0]['masterUrl']
                            util.download_file_2(video_url, user, f'{note_id}.mp4')
                            time.sleep(5)
    logger.info('等待新视频……')
    time.sleep(time_interval)
