#!/usr/bin/env python
# coding: utf-8

import json
import os
import pandas as pd
import numpy as np
from datetime import *
from dateutil.relativedelta import relativedelta
import calendar
from sqlalchemy import create_engine
import pymysql
pymysql.install_as_MySQLdb()

# 获取月度结束日期
def getMonthEndDate(date):
    date = str(date)
    year = date.split("-")[0]
    month = date.split("-")[1]
    this_month_end = datetime(int(year),int(month),calendar.monthrange(int(year),int(month))[1])
    return this_month_end

# 获取周度结束日期
def getWeekEndDate(date):
    date = datetime.strptime(date, "%Y-%m-%d")
    week_num = date.weekday()
    this_week_end = date + relativedelta(days = 6-week_num)
    return this_week_end

# 周度日期标准化
def dateStand(data, freq):
    temp_data = data["日期"].apply(lambda x: str(x).split(" ")[0])
    start_date = temp_data.iloc[0]
    end_date = temp_data.iloc[-1]
    data["日期"] = data["日期"].apply(lambda x: str(x).split(" ")[0])
    metric_id = list(data.columns)[1]
    if freq == "周":
        # 时间序列生成
        result = pd.DataFrame(pd.date_range(start=start_date, end=end_date, freq="D"), columns=["日期"])
        result["判断周日"] = result["日期"].apply(lambda x: x.weekday() == 6)
        result = result[result["判断周日"] == True]
        result = result.reset_index(drop=True, inplace=False)
        result = result[["日期"]]
        # 原始数据处理
        data["日期"] = data["日期"].apply(getWeekEndDate)
        data["日期"] = data["日期"].apply(lambda x: str(x).split(" ")[0])
        # 按照周度聚合,兼容数据库中存在周度数据按照日度存储的情况
        new_data = data.groupby("日期")[metric_id].mean().reset_index()
        new_data.columns = ["日期",metric_id]
        result["日期"] = result["日期"].apply(lambda x: str(x).split(" ")[0])
        final_result = pd.merge(left=result, right=new_data, on="日期", how="left")
    elif freq == "月":
        # 时间序列生成
        result = pd.DataFrame(pd.date_range(start=start_date, end=end_date, freq="M"), columns=["日期"])
        data["日期"] = data["日期"].apply(getMonthEndDate)
        data["日期"] = data["日期"].apply(lambda x: str(x).split(" ")[0])
        result["日期"] = result["日期"].apply(lambda x: str(x).split(" ")[0])
        final_result = pd.merge(left=result, right=data, on="日期", how="left")
    else:
        # 时间序列生成
        result = pd.DataFrame(pd.date_range(start=start_date, end=end_date, freq="D"), columns=["日期"])
        data["日期"] = data["日期"].apply(lambda x: str(x).split(" ")[0])
        result["日期"] = result["日期"].apply(lambda x: str(x).split(" ")[0])
        final_result = pd.merge(left=result, right=data, on="日期", how="left")
    return final_result

# 相关系数计算方法
def pearsonSim(data):
    columns = data.columns
    a = data[columns[1]].values
    b = data[columns[2]].values
    result = np.corrcoef(a, b)
    result = result[0][-1]
    return np.round(result, 4)

# 针对待匹配数据频率转换
def convertFreq(data, base_freq, target_freq):
    '''
    日-周 日-月 周-月
    '''
    # 数据标准化
    data = dateStand(data, base_freq)
    metric_id = list(data.columns)[1]
    if base_freq == "日" and target_freq == "周":
        data["日期"] = data["日期"].apply(getWeekEndDate)
        new_data = data.groupby("日期")[metric_id].mean().reset_index()
        new_data.columns = ["日期", metric_id]
    elif base_freq == "日" and target_freq == "月":
        data["日期"] = data["日期"].apply(getMonthEndDate)
        new_data = data.groupby("日期")[metric_id].mean().reset_index()
        new_data.columns = ["日期", metric_id]
    elif base_freq == "周" and target_freq == "月":
        data["日期"] = data["日期"].apply(getMonthEndDate)
        new_data = data.groupby("日期")[metric_id].mean().reset_index()
        new_data.columns = ["日期", metric_id]
    else:
        new_data = data
    return new_data

# 逐条计算
def catchDataFromSqlAndCal(config_data, sql_config):
    print(sql_config.columns)
    main_data = pd.read_excel(config_data["file"])
    main_freq = config_data["freq"]
    main_data = dateStand(main_data, main_freq)

    # 保存最后的结果
    metric_result = []
    for temp_data in sql_config.values:
        temp_sql = temp_data[-1]
        temp_database = temp_data[-2]
        temp_index_id = temp_data[0]
        temp_name = temp_data[1]
        temp_freq = temp_data[2]

        # 从数据库中抽取数据
        temp_con = create_engine('mysql://root:root@192.168.1.15:3306/{}_database'.format(temp_database))
        temp_data = pd.read_sql(temp_sql, con=temp_con)
        if temp_data.shape[0] == 0:
            continue
        else:
            temp_data = temp_data[["date", "value"]]
            temp_data.columns = ["日期", temp_name]
        
            # 数据标准化
            temp_data = dateStand(temp_data, temp_freq)
        
            # 同频混频处理
            if main_freq != temp_freq:
                temp_data = convertFreq(temp_data, main_freq, temp_freq)
        
            temp_final_data = pd.merge(left=temp_data, right=main_data, on="日期", how="left")
            # 指标计算
            temp_metric = pearsonSim(temp_final_data)
            # 保存
            metric_result.append([temp_index_id, temp_metric])
    metric_result = pd.DataFrame(metric_result, columns=["index_id","余弦相似度"])
    update_result = pd.merge(left=sql_config, right=metric_result,on="index_id",how="right")
    update_result = update_result.sort_values(by="余弦相似度", ascending=False, inplace=False)
    return update_result