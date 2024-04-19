#!/usr/bin/env python3.9
# coding: utf-8

from os import system
from pathlib import Path

import matplotlib.pyplot as plt

plt.ion()  # enable interactive mode

folder = Path(input("Frame folder? ")).resolve()

fig, ax = plt.subplots(figsize=(4.6, 4.6))

# show first frame, draw interactively on this image object
im = ax.imshow(plt.imread(Path(input("First frame? ")).resolve()))
ax.axis("off")


def draw_frame(fig, ax, frame_path: Path):
    global im

    image_j = plt.imread(frame_path)

    # show next frame
    im.set_array(image_j)

    fig.canvas.draw()
    fig.canvas.flush_events()


frames = iter(folder / f"frame{j}.jpg" for j in range(1000))
frame = next(frames)

while True:
    wait_for_me = input(f"Draw {frame.name}? ")
    if wait_for_me:
        if str.lower(wait_for_me) == "exit":
            # end program on 'exit', stop drawing
            break
        else:
            # wait again on not None, also on not 'exit'
            continue
    try:
        draw_frame(fig, ax, frame)
        drew = True

    # try to draw. if you can't then just ask for input again
    except Exception as err:
        drew = False
    finally:
        system("cls || clear")

    if drew:
        frame = next(frames)
    else:
        frame = frame


plt.show()
