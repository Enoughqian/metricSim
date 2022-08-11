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
from fastdtw import fastdtw
from scipy.stats import pearsonr
from copy import deepcopy
from scipy.spatial.distance import euclidean
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

def getRankByMetric(data):
    # 获取每个指标的排名
    columns = list(data.columns)
    columns = [i for i in columns if i != "日期"]
    rank_columns = []
    for i in columns:
        if "距离" in i:
            data = data.sort_values(by=i, ascending=True, inplace=False)
        elif "系数" in i:
            data = data.sort_values(by=i, ascending=False, inplace=False)
        else:
            continue
        data[i+"_rank"] = [i+1 for i in range(len(data))]
        rank_columns.append(i+"_rank")
    # 排名求和
    data["Rank"] = 0
    for i in rank_columns:
        data["Rank"] += data[i]
    # 获取总的排名
    data = data.sort_values(by="Rank", ascending=True, inplace=False)
    data["Rank"] = [i+1 for i in range(len(data))]
    data = data[[i for i in data.columns if i not in rank_columns]]
    return data

# 数据预处理
def normalRegularization(data):
    columns1 = list(data.columns)[1]
    columns2 = list(data.columns)[2]
    x = data[columns1].values
    y = data[columns2].values
    x_min = min(x)
    y_min = min(y)
    x_max = max(x)
    y_max = max(y)
    x = [(i - x_min)/(x_max - x_min) for i in x]
    y = [(i - y_min)/(y_max - y_min) for i in y]
    return x, y

# 欧几里得距离
def EuclidDistanceOne(data):
    # 基于欧几里得距离的相似度计算
    x = data[0]
    y = data[1]
    result = []
    
    for i in range(len(x)):        
        result.append(abs(x[i] - y[i]))
    result = np.sum(result)
    return result

# 欧几里得距离
def EuclidDistanceTwo(data):
    # 基于欧几里得距离的相似度计算
    x = data[0]
    y = data[1]
    result = []

    for i in range(len(x)):
        result.append(np.power(abs(x[i] - y[i]), 2))
    result = np.sqrt(np.sum(result))
    return result

# 皮尔逊相关系数
def PearsonSim(data):
    # 基于相关性的相似度计算
    x = data[0]
    y = data[1]
    p, r = pearsonr(x, y)
    return p

# corr相关系数
def CorrelationSim(data):
    x = data[0]
    y = data[1]
    diff1 = np.diff(np.array(x))
    diff2 = np.diff(np.array(y))
    TCC = np.sum(diff1*diff2)/(np.sqrt(np.sum(np.power(diff1, 2))) * np.sqrt(np.sum(np.power(diff2, 2))))
    return TCC

# dtw距离
def dtwDistance(data):
    x = data[0]
    y = data[1]
    distance, path = fastdtw(x, y, dist=euclidean)
    return distance

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
    main_data = pd.read_excel(config_data["file"])
    main_freq = config_data["freq"]
    rank_limit = int(config_data["ranknum"])
    metric_list = config_data["metric"]
    main_data = dateStand(main_data, main_freq)
    # 方法和列名的映射关系
    metric_map = {
        "EuclidDistanceOne": "欧式距离一阶",
        "EuclidDistanceTwo": "欧式距离二阶",
        "PearsonSim": "皮尔逊相关系数",
        "CorrelationSim": "Corr相关系数",
        "dtwDistance": "dtw距离"
    }

    # 保存最后的结果
    metric_result = []
    for temp_data in sql_config.values:
        # 取出需要计算的信息
        temp_sql = temp_data[-1]
        temp_database = temp_data[-2]
        temp_index_id = temp_data[0]
        temp_name = temp_data[1]
        temp_freq = temp_data[2]

        # 计算结果
        temp_result = [temp_index_id]
        # 从数据库中抽取数据
        temp_con = create_engine('mysql://root:root@192.168.1.15:3306/{}_database'.format(temp_database))
        temp_data = pd.read_sql(temp_sql, con=temp_con)
        if temp_data.shape[0] == 0 or len(temp_data["value"].unique()) == 1:
            continue
        else:
            temp_data = temp_data[["date", "value"]]
            temp_data.columns = ["日期", temp_name]
        
            # 数据日期标准化
            temp_data = dateStand(temp_data, temp_freq)
        
            # 同频混频处理
            if main_freq != temp_freq:
                temp_data = convertFreq(temp_data, main_freq, temp_freq)
        
            temp_final_data = pd.merge(left=temp_data, right=main_data, on="日期", how="left")
            
            # 数据预处理
            test_data_normal = normalRegularization(temp_final_data)

            # 数据指标计算
            temp_cal_result = [k+"(test_data_normal)" for k in metric_list]
            
            # 计算结果
            for w in temp_cal_result:
                temp_metric_result = eval(w)
                temp_metric_result = round(float(temp_metric_result), 5)
                temp_result.append(temp_metric_result)
            # 保存
            metric_result.append(temp_result)
        temp_con.dispose()
    # 输出的列名
    columns_result = ["index_id"]
    columns_result.extend([metric_map[m] for m in metric_list])
    metric_result = pd.DataFrame(metric_result, columns = columns_result)
    # 数据拼接
    update_result = pd.merge(left=sql_config, right=metric_result,on="index_id",how="right")
    update_result = getRankByMetric(update_result)
    update_result = update_result.sort_values(by="Rank", ascending=True, inplace=False)
    # 按照最后的结果筛选
    update_result = update_result[update_result["Rank"] <= rank_limit]

    # 构造绘图数据
    k = 0
    plot_result = deepcopy(main_data)
    for temp_info in update_result.values:
        temp_metric_name = temp_info[1]
        temp_rank_num = str(temp_info[-1])
        temp_new_name = temp_rank_num+"_"+temp_metric_name
        temp_sql = temp_info[6]
        temp_database = temp_info[5]

        # 数据抽取
        temp_con = create_engine('mysql://root:root@192.168.1.15:3306/{}_database'.format(temp_database))
        temp_data = pd.read_sql(temp_sql, con=temp_con)

        temp_data = temp_data[["date", "value"]]
        temp_data.columns = ["日期", temp_name]
        
        # 数据日期标准化
        temp_data = dateStand(temp_data, temp_freq)
        
        # 同频混频处理
        if main_freq != temp_freq:
            temp_data = convertFreq(temp_data, main_freq, temp_freq)
        # 新列名
        temp_data.columns = ["日期", temp_new_name]

        # 数据拼接
        plot_result = pd.merge(right=temp_data, left=plot_result, on="日期", how="right")
    
    return update_result, plot_result