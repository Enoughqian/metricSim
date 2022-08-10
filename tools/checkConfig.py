#!/usr/bin/env python
# coding: utf-8

import pandas as pd
import numpy as np
import json
import re
import os
from datetime import *
import calendar
from dateutil.relativedelta import relativedelta

# 获取最后的起止时间
def checkStartEndDate(data_path, date_type):
    # 读取数据
    data = pd.read_excel(data_path)
    # 获取起始日期和结束日期
    temp_data = data["日期"].apply(lambda x: str(x).split(" ")[0]).values
    data_start = temp_data[0]
    data_end = temp_data[-1]
    data_start = datetime.date(pd.to_datetime(data_start))
    data_end = datetime.date(pd.to_datetime(data_end))
    # 根据时间状态获取时间
    now_date = datetime.date(datetime.now())
    print(date_type)
    if date_type == "RecentThree":
        start = datetime.date(datetime.now() - relativedelta(years=3))
    elif date_type == "RecentSix":
        start = datetime.date(datetime.now() - relativedelta(years=6))
    elif date_type == "RecentTen":
        start = datetime.date(datetime.now() - relativedelta(years=10))
    else:
        start = datetime.date(pd.to_datetime("2007-01-01"))
    final_start_date = max(data_start, start)
    final_end_date = min(now_date, data_end)
    if final_start_date < final_end_date:
        # 日期处理
        final_start_date = str(final_start_date).split(" ")[0]
        final_end_date = str(final_end_date).split(" ")[0]
        return ("日期格式正常", [final_start_date, final_end_date])
    else: 
        return ("日期格式错误", [])
