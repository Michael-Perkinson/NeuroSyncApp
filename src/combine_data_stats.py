from PIL import Image, ImageTk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.patches import Rectangle
from openpyxl import load_workbook
from openpyxl.styles import Border, Side
from scipy.integrate import simps
from tkinter import Canvas
from tkinter import Toplevel
from tkinter import colorchooser, BooleanVar, Frame, Scrollbar, Canvas, Checkbutton
from tkinter import filedialog
from tkinter import messagebox
from tkinter import simpledialog
from tkinter import ttk
from openpyxl.styles import Font
import atexit
import cProfile
import csv
import hashlib
import json
import matplotlib
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator
import matplotlib.ticker as ticker
import numpy as np
import os
import pandas as pd
import pstats
import psutil
import re
import scipy
from scipy import integrate
import signal
import threading
import time
import tkinter as tk
from tkinter import colorchooser
import tkinter.colorchooser as colourchooser
import tkinter.font as tkf
import uuid
import webcolors