'''
Author: glider
Date: 2024-08-03 10:10:48
LastEditTime: 2024-08-03 10:13:48
FilePath: /ffmpeg_ws/stt/1.py
Version:  v0.011.MP3
Description: 
************************************************************************
Copyright (c) 2024 by  ${git_email}, All Rights Reserved. 
************************************************************************
'''
import subprocess
import speech_recognition as sr

def convert_mp3_to_wav(mp3_file_path, wav_file_path):
    """
    使用 ffmpeg 将 MP3 文件转换为 WAV 格式。
    """
    command = ['ffmpeg', '-i', mp3_file_path, '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1', wav_file_path]
    subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def recognize_speech_from_wav(wav_file_path):
    """
    从 WAV 文件识别语音并打印转换后的文本。
    """
    r = sr.Recognizer()
    with sr.AudioFile(wav_file_path) as source:
        audio = r.record(source)  # 读取整个音频文件

    # 尝试使用 Google 语音识别
    try:
        text = r.recognize_google(audio, language='zh-CN')
        print("Recognized text:", text)
    except sr.UnknownValueError:
        print("Google Speech Recognition could not understand audio")
    except sr.RequestError as e:
        print(f"Could not request results from Google Speech Recognition service; {e}")

if __name__ == '__main__':
    mp3_file = '1.mp3'
    wav_file = '1_converted.wav'
    convert_mp3_to_wav(mp3_file, wav_file)
    recognize_speech_from_wav(wav_file)
