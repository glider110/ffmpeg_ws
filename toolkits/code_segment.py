'''
Author: glider
Date: 2024-07-23 21:16:03
LastEditTime: 2024-07-24 21:25:17
FilePath: /ffmpeg_ws/code_segment.py
Version:  v0.01
Description: 
************************************************************************
Copyright (c) 2024 by  ${git_email}, All Rights Reserved. 
************************************************************************
'''
ffmpeg -y -i "input_file" -hide_banner -map_metadata 0 -metadata handler_name=@Cairl -vf "lut3d=luts/selected_lut_file" "output_file"


ffmpeg -y -i "first_part.mp4" -hide_banner -map_metadata 0 -metadata handler_name=@Cairl -vf "lut3d=1.cube" "cube.mp4"