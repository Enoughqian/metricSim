#!/usr/bin/env python
# coding: utf-8

import pandas as pd
import numpy as np
import json
import re
import os
from datetime import *
import calendar

# 获取月末日期
def getMonthEndDate(date):
    date = str(date)
    year = date.split("-")[0]
    month = date.split("-")[1]
    this_month_end = datetime(int(year),int(month),calendar.monthrange(int(year),int(month))[1])
    return str(this_month_end).split(" ")[0]

# 数据检查
def judgeData(path):
    data = pd.read_excel(path)
    err_info = "正常"
    freq = "未确定"
    if list(data.columns)[0] != "日期":
        err_info = "头中缺少日期列"
    elif list(data.columns)[1] == "Unnamed: 1":
        err_info = "表头中缺少指标列"
    else:
        None1_data = data[data["日期"].isna() == True]
        None2_data = data[data[list(data.columns)[1]].isna() == True]
        if None1_data.shape[0] != 0:
            err_info = "日期列中存在缺失值"
        elif None2_data.shape[0] != 0:
            err_info = "{}值中存在缺失值".format(list(data.columns)[1])
        else:
            date_list = data["日期"].to_list()
            result = []
            for i in range(len(date_list) - 1):
                now_date = date_list[i]
                next_date = date_list[i+1]
                during = (next_date - now_date).days
                result.append(during)
            result = list(set(result))
            if len(result) == 1 and result[0] == 1:
                freq = "日"
            elif len(result) == 1 and result[0] == 7:
                freq = "周"
            else:
                date_list = [str(i).split(" ")[0] for i in date_list]
                start_date = date_list[0]
                end_date = date_list[-1]
                new_date = pd.DataFrame(pd.date_range(start=start_date, end=end_date, freq="M"), columns=["日期"])
                new_date = new_date["日期"].apply(lambda x: str(x).split(" ")[0]).to_list()
                if date_list == new_date:
                    freq = "月"
                else:
                    err_info = "数据日期异常，请检查"
    return (freq, err_info)

