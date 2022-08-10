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

# 生成数据库的配置文件
def genDBConfig(input_json):
    # 获取基本信息
    freq_state = input_json["freqtype"]
    freq = input_json["freq"]
    date_type = input_json["date"]
    select_database = input_json["dbname"]
    now_data = pd.read_excel(input_json["file"])
    start_date = input_json["start_date"]
    end_date = input_json["end_date"]
    # 
    k = 0
    database_config = pd.read_excel("config/dbconfig.xlsx")
    database_config = database_config[database_config["数据库名称"].isin(select_database)]
    # 数据处理
    for database_info in database_config[["数据库名称", "信息"]].values:
        # 建立连接
        temp_con = create_engine('mysql://root:root@192.168.1.15:3306/{}_database'.format(database_info[0]))
        if database_info[1] == "月度数据":
            temp_data = pd.read_sql("select * from metadata", con = temp_con)
            temp_data["db_name"] = database_info[0]
        elif database_info[1] == "日度数据":
            temp_data = pd.read_sql("select * from metadata_daily", con = temp_con)
            temp_data["db_name"] = database_info[0]
        else:
            temp_data1 = pd.read_sql("select * from metadata", con = temp_con)
            temp_data1["db_name"] = database_info[0]
            temp_data2 = pd.read_sql("select * from metadata_daily", con = temp_con)
            temp_data2["db_name"] = database_info[0]
            temp_data = pd.concat([temp_data1, temp_data2], axis=0)
        # 数据拼接
        if k == 0:
            result = temp_data
        else:
            result = pd.concat([result, temp_data], axis=0)
        k += 1

    # 混频情况筛选
    target_freq = []
    if freq == "日":
        target_freq = []
    elif freq == "周":
        target_freq = ["日"]
    else:
        target_freq = ["日", "周"]
    
    # 不同情况判断
    if freq_state == "SameFreq":
        result = result[result["frequency"] == freq]
    elif freq_state == "DiffFreq":
        result = result[result["frequency"].isin(target_freq)]
    elif freq_state == "AllFreq":
        target_freq.append(freq)
        result = result[result["frequency"].isin(target_freq)]
    
    # 生成对应的sqlquery
    sql_list = []
    result = result[["index_id", "index_name", "frequency", "tag", "type", "db_name"]]
    result = result.drop_duplicates(subset=["index_id"], inplace=False, keep="first")
    for temp in result.values:
        if temp[2] == "月":
            sql_list.append("select * from final_data_value where index_id = '{}' and date >= '{}' and date <= '{}';".format(temp[0], start_date, end_date))
        else:
            sql_list.append("select * from daily_data_value where index_id = '{}' and date >= '{}' and date <= '{}';".format(temp[0], start_date, end_date))
    result["sql_query"] = sql_list
    result = result.reset_index(drop=True, inplace=False)
    result.to_csv("temp/dbconfig.csv", index=None)
