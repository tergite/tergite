import matplotlib as mpl

from pylab import *
from qutip import *
from matplotlib import cm
import imageio

from tqdm import tqdm


def animate_bloch(states, duration=0.1, save_all=False, filename:str='default'):
    b = Bloch()
    b.vector_color = ['r']
    b.view = [-40, 30]

    images = []
    try:
        length = len(states)
    except:
        length = 1
        states = [states]

    ## normalize colors to the length of data ##
    nrm = mpl.colors.Normalize(0, length)
    colors = cm.cool(nrm(range(length)))  # options: cool, summer, winter, autumn etc.

    ## customize sphere properties ##
    b.point_color = list(colors)  # options: 'r', 'g', 'b' etc.
    b.point_marker = ['o']
    b.point_size = [30]

    for i in tqdm(range(length), desc='Animate thetas on bloch sphere', unit='iteration'):
        b.clear()
        b.add_states(states[i])
        b.add_states(states[:(i + 1)], 'point')

        if save_all:
            b.save(dirc='tmp')  # saving images to tmp directory
            filename = "tmp/bloch_%01d.png" % i
        else:
            filename = 'temp_file.png'
            b.save(filename)

        images.append(imageio.imread(filename))

    imageio.mimsave(f'{filename}.gif', images, duration=duration)
