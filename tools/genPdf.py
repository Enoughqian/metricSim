#!/usr/bin/env python
# coding: utf-8

import os
import pandas as pd
import numpy as np
import matplotlib.pylab as plt  # 导入绘图包
import matplotlib.pyplot as mp
from matplotlib.font_manager import FontProperties
from matplotlib.backends.backend_pdf import PdfPages
from pylab import *  #图像中的title,xlabel,ylabel均使用中文
from datetime import *

# 绘制图形
def plot_pages(data_path, pdf_path):
    data = pd.read_csv(data_path, encoding="GBK")
    pdf = PdfPages(pdf_path)
    fig = plt.figure(figsize=(10, 6 * (data.shape[1] - 2)))
    myfont = FontProperties(fname=r"C:\Windows\Fonts\simhei.ttf")
    mpl.rcParams['axes.unicode_minus'] = False


    xlable = data.iloc[:, 0]
    y = data.iloc[:, 1]
    for i in range(2, data.shape[1]):
        mpl.rcParams['axes.unicode_minus'] = False
        x = data.iloc[:, i]

        ax1 = fig.add_subplot((data.shape[1] - 2), 1, i-1)
        ax1.plot(xlable, y, 'o-', markersize=0.2, c='orangered',label='y', linewidth = 1) #绘制折线图像1,圆形点，标签，线宽
        plt.title("Rank: " + data.columns[i].split("_")[0], fontsize=12)
        plt.legend(loc=2)

        ax2 = ax1.twinx() # 创建第二个坐标轴
        ax2.plot(xlable, x, 'o-', markersize=0.2, c='blue',label='x', linewidth = 1) #同上
        plt.legend(loc=1)


        ax1.set_xlabel('时间', fontproperties=myfont,size=15)
        ax1.set_ylabel(data.columns[1], fontproperties=myfont, size=12)
        ax2.set_ylabel(data.columns[i].strip(data.columns[i].split("_")[0] + "_"), fontproperties=myfont, size=12)
        plt.tight_layout()

    pdf.savefig()
    plt.close()
    pdf.close()