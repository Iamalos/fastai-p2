# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/11_initializing.ipynb.

# %% auto 0
__all__ = ['clean_ipython_hist', 'clean_tb', 'clean_mem', 'BatchTransformCB', 'GeneralRelu', 'plot_func', 'init_weights',
           'lsuv_init', 'conv', 'get_model']

# %% ../nbs/11_initializing.ipynb 3
import pickle,gzip,math,os,time,shutil,torch,matplotlib as mpl,numpy as np,matplotlib.pyplot as plt
import sys,gc,traceback
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
from torcheval.metrics import MulticlassAccuracy
from datasets import load_dataset,load_dataset_builder

from .datasets import *
from .conv import *
from .learner import *
from .activations import *

# %% ../nbs/11_initializing.ipynb 20
def clean_ipython_hist():
    # Code in this function mainly copied from IPython source
    if not 'get_ipython' in globals(): return
    ip = get_ipython()
    user_ns = ip.user_ns
    ip.displayhook.flush()
    pc = ip.displayhook.prompt_count + 1
    for n in range(1, pc): user_ns.pop('_i'+repr(n),None)
    user_ns.update(dict(_i='',_ii='',_iii=''))
    hm = ip.history_manager
    hm.input_hist_parsed[:] = [''] * pc
    hm.input_hist_raw[:] = [''] * pc
    hm._i = hm._ii = hm._iii = hm._i00 =  ''
     

# %% ../nbs/11_initializing.ipynb 21
def clean_tb():
    # h/t Piotr Czapla
    if hasattr(sys, 'last_traceback'):
        traceback.clear_frames(sys.last_traceback)
        delattr(sys, 'last_traceback')
    if hasattr(sys, 'last_type'): delattr(sys, 'last_type')
    if hasattr(sys, 'last_value'): delattr(sys, 'last_value')
     

# %% ../nbs/11_initializing.ipynb 22
def clean_mem():
    clean_tb()
    clean_ipython_hist()
    gc.collect()
    torch.cuda.empty_cache()
     

# %% ../nbs/11_initializing.ipynb 93
class BatchTransformCB(Callback):
    # tfm can be nn.Sequential in order to combine several transforms
    def __init__(self, tfm, on_train=True, on_val=True): fc.store_attr()
    
    def before_batch(self, learn):
        if (self.on_train and learn.training) or (self.on_val and not learn.training):
            # transform batch during the `before_batch` stage
            learn.batch = self.tfm(learn.batch)

# %% ../nbs/11_initializing.ipynb 104
class GeneralRelu(nn.Module):
    def __init__(self, leak=None, sub=None, maxv=None):
        super().__init__()
        fc.store_attr()
        
    def forward(self, x):
        x = F.leaky_relu(x, self.leak) if self.leak is not None else F.relu(x)
        if self.sub is not None: x -= self.sub
        if self.maxv is not None: x.clamp_max_(self.maxv)
        return x

# %% ../nbs/11_initializing.ipynb 106
def plot_func(f, start=-5, end=5, steps=100):
    # setup x
    x = torch.linspace(start,end,steps)
    # plot function
    plt.plot(x, f(x))
    # setup grid lines
    plt.grid(True, which='both', ls='--')
    # setup vertical and horizontal lines at (0,0)
    plt.axhline(y=0, color='k', linewidth=0.7)
    plt.axvline(x=0, color='k', linewidth=0.7)

# %% ../nbs/11_initializing.ipynb 110
def init_weights(m, leaky=0.):
    # init kaiming normal for conv layers
    if isinstance(m, (nn.Conv1d, nn.Conv2d, nn.Conv3d)): 
        init.kaiming_normal_(m.weight, a=leaky)

# %% ../nbs/11_initializing.ipynb 120
def _lsuv_stats(hook, # hook object
                mod, # module to hook onto
                inp, # input to a layer (x or output from previous layer)
                outp # output - activations of a model's layer
               ):
    acts = to_cpu(outp)
    hook.mean = acts.mean()
    hook.std = acts.std()
    
def lsuv_init(model,
              m, # list of output modules
              m_in, # list of input modules
              xb # batch
             ):
    # create a hook to a module using `_lsuv_stats` f-n
    # import ipdb; ipdb.set_trace()
    h = Hook(m, _lsuv_stats)
    # without grad calculation update weights and biases until std of layer's activations is 1 and mean is 0
    with torch.no_grad():
        while model(xb) is not None and (abs(h.std-1)>1e-3 or abs(h.mean)>1e-3):
            m_in.bias -= h.mean
            m_in.weight.data /= h.std
    h.remove()

# %% ../nbs/11_initializing.ipynb 134
def conv(ni, nf, ks=3, stride=2, act=nn.ReLU, norm=None, bias=None):
    # if Normalization is of type BN, than we don't need bias
    if bias is None: bias = not isinstance(norm, (nn.BatchNorm1d, nn.BatchNorm2d, nn.BatchNorm3d))
    # conv2d layer
    layers = [nn.Conv2d(ni, nf, stride=stride, kernel_size=ks, padding=ks//2, bias=bias)]
    # append normalization layer if needed
    if norm: layers.append(norm(nf))
    # append activation layer if needed
    if act: layers.append(act())
    # pull all layers into Sequential
    return nn.Sequential(*layers)          

# %% ../nbs/11_initializing.ipynb 135
def get_model(act=nn.ReLU, nfs=None, norm=None):
    # standard number of filters ([1,8,16,32,64])
    if nfs is None: nfs = [1,8,16,32,64]
    # conv layers for given filters
    layers = [conv(nfs[i], nfs[i+1], act=act, norm=norm) for i in range(len(nfs)-1)]
    #  pull together with final layers without activation of normalization. Then flatten and move to device
    return nn.Sequential(*layers, conv(nfs[-1], 10,act=None, norm=False, bias=True), 
                         nn.Flatten()).to(def_device)
