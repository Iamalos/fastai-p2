# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/13_resnet.ipynb.

# %% auto 0
__all__ = ['act_gr', 'ResBlock']

# %% ../nbs/13_resnet.ipynb 3
import pickle,gzip,math,os,time,shutil,torch,matplotlib as mpl,numpy as np,matplotlib.pyplot as plt
import fastcore.all as fc
from collections.abc import Mapping
from pathlib import Path
from operator import attrgetter,itemgetter
from functools import partial
from copy import copy
from contextlib import contextmanager

import torchvision.transforms.functional as TF,torch.nn.functional as F
from torch import tensor,nn,optim
from torch.utils.data import DataLoader,default_collate
from torch.nn import init
from torch.optim import lr_scheduler
from torcheval.metrics import MulticlassAccuracy
from datasets import load_dataset,load_dataset_builder

from .datasets import *
from .conv import *
from .learner import *
from .activations import *
from .init import *
from .sgd import *

# %% ../nbs/13_resnet.ipynb 9
act_gr = partial(GeneralRelu, leak=0.1, sub=0.4)

# %% ../nbs/13_resnet.ipynb 21
# conv_block if conv2(conv1(in)). for conv2 don't use activation
def _conv_block(ni, nf, stride, act=act_gr, norm=None, ks=3):
    # if norm: init.constant_(conv2[1].weight, 0.)
    return nn.Sequential(conv(ni, nf, stride=1, act=act, norm=norm, ks=ks),
                         conv(nf, nf, stride=stride, act=None, norm=norm, ks=ks))

class ResBlock(nn.Module):
    def __init__(self, ni, nf, stride=1, ks=3, act=act_gr, norm=None):
        super().__init__()
        # create conv2(conv1(in))
        self.convs = _conv_block(ni, nf, stride, act, norm, ks)
        # create idconvolution if ni and nf filters are not equal. 
        # Use minimum efforts (ks and stride are 1)
        self.idconv = fc.noop if ni==nf else conv(ni, nf, ks=1, stride=1, act=None)
        # if stride is not 1 (but 2) use Average pool
        self.pool = fc.noop if stride==1 else nn.AvgPool2d(2, ceil_mode=True)
        # apply activation
        self.act = act()
    
    def forward(self, x): return self.act(self.convs(x) + self.idconv(self.pool(x)))  