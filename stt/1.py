'''
Author: glider
Date: 2024-08-03 10:10:48
LastEditTime: 2024-08-03 10:37:16
FilePath: /ffmpeg_ws/stt/1.py
Version:  v0.011.MP3
Description: 
************************************************************************
Copyright (c) 2024 by  ${git_email}, All Rights Reserved. 
************************************************************************
'''
# import speech_recognition as sr

# # 创建一个Recognizer对象
# r = sr.Recognizer()

# # 从音频文件中读取音频数据
# with sr.AudioFile('output_audio1.wav') as source:
#     # 监听源音频
#     audio = r.record(source)

# # 使用Google语音识别引擎将音频数据转换为文本
# try:
#     text = r.recognize_google(audio, language='zh-CN')
#     print(text)
# except sr.UnknownValueError:
#     print("Google Speech Recognition could not understand audio")
# except sr.RequestError as e:
#     print(f"Could not request results from Google Speech Recognition service; {e}")


import speech_recognition as sr

# 创建一个 Recognizer 实例
recognizer = sr.Recognizer()

# 从音频文件中加载音频
audio_file = "output_audio1.wav"
with sr.AudioFile(audio_file) as source:
    audio_data = recognizer.record(source)  # 读取整个音频文件

# 使用 Google Web Speech API 进行语音识别
try:
    # 默认使用英语，可以通过language参数指定其他语言，如中文 'zh-CN'
    text = recognizer.recognize_google(audio_data, language='en-US')
    print("识别结果：")
    print(text)
except sr.UnknownValueError:
    print("Google Web Speech API 无法识别音频")
except sr.RequestError as e:
    print(f"Google Web Speech API 请求失败; {e}")
