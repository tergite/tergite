#!/usr/bin/env python3.9
# coding: utf-8

import time
from datetime import datetime
from os import listdir, makedirs
from pathlib import Path
from shutil import move

import numpy as np
from PIL import Image

folder = Path("testdata").resolve()


def save_old_frames():
    global folder
    saved_folder = folder / "saved_animations"
    makedirs(saved_folder, exist_ok=True)

    old_frames = [f for f in listdir(folder) if f.endswith(".jpg")]

    if len(old_frames):
        now_time = datetime.now()
        mstr = now_time.strftime("%Y%m%d%H%M%S")
        new_dir = saved_folder / mstr
        makedirs(new_dir, exist_ok=True)
        for f in old_frames:
            move(folder / f, new_dir / f)


save_old_frames()


def compute_new_frame(j: int):
    # Do some labour, which computes a frame and saves
    # to a folder...
    noise = np.random.rand(50, 50)
    img = Image.fromarray(noise, "RGB")
    img.save(folder / f"frame{j}.jpg")

    # emulate time it actually takes to compute frame
    time.sleep(np.random.rand() * 5)


[compute_new_frame(j) for j in range(20) if not print("#", end="", flush=True)]
print()
