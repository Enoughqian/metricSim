#!/usr/bin/env python
# coding: utf-8

import requests
from datetime import *
import json
import os
import pandas as pd
from werkzeug.utils import secure_filename
from flask_cors import *
from flask import Flask,render_template,request,Response,redirect,url_for, jsonify,g,send_from_directory,send_file
from tools.checkInput import *
from tools.genDataBaseConfig import *
from tools.checkConfig import *
from tools.calMetric import *

# 构造flask服务
app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

# 主页面
@app.route("/")
def hello_world():
    return render_template("demo.html")

# 上传文件
@app.route('/upload_file', methods=['POST', 'GET'])
def upload():
    if request.method == 'POST':
        f = request.files['file']
        basepath = os.path.dirname(__file__)
        file_name = str(datetime.now()).split(" ")[1].replace(":", "").split(".")[0]
        dir_path = str(datetime.now()).split(" ")[0].replace("-","")
        upload_path = os.path.join(basepath, 'uploads/'+dir_path)
        
        # 判断文件夹是否存在
        if not os.path.exists(upload_path):
            os.mkdir(upload_path)
        
        # 拼接数据保存路径
        file_path = str(file_name)+str(f.filename)
        f.save(upload_path+"/"+file_path)

        # 数据读取
        path = upload_path+"/"+file_path
        data = pd.read_excel(path)
        
        # 数据检查
        judge_result = judgeData(path)
        
        # 异常数据删除
        print(judge_result[1])
        if judge_result[1] != "正常":
            os.remove(path)
        else:
            with open("temp/records.txt", "w", encoding="GBK") as f:
                temp_content = path+"\n"+judge_result[0]
                f.write(temp_content)
        return_content = {"数据状态": judge_result[1], "数据频率": judge_result[0]}
    return jsonify(return_content)

# 传入配置信息
@app.route("/config", methods=["POST"])
def form_data():
    data = request.get_data()
    data = eval(data)
    with open("temp/records.txt", "r", encoding="GBK") as f:
        temp = f.read().strip().split("\n")
        file_path = temp[0]
        freq = temp[1]
    
    data["file"] = file_path
    data["freq"] = freq
    data["date"] = data["date"][0]
    data["freqtype"] = data["freqtype"][0]
    data["ranknum"] = data["ranknum"][0]
    
    checkresult = checkStartEndDate(file_path, data["date"])
    if checkresult[0] == "日期格式正常":
        
        data["start_date"] = checkresult[1][0]
        data["end_date"] = checkresult[1][1]
        # 数据保存
        with open("temp/config.json", "w") as f:
            json.dump(data, f)
        return jsonify(data)
    else:
        return jsonify(checkresult[0])

# 点击运行开始计算
@app.route("/calculate", methods=["post"])
def calculate_data():
    data = request.get_data()
    data = json.loads(eval(data))

    # 生成sql配置文件
    genDBConfig(data)
    # 开始计算
    sql_config = pd.read_csv("temp/dbconfig.csv")
    cal_result = catchDataFromSqlAndCal(data, sql_config)
    cal_result.to_csv("temp/sim_result.csv", index=None, encoding="GBK")
    return "成功"

# 结果下载
@app.route("/download", methods=['GET'])
def download_file():
    return send_file("temp/sim_result.csv", as_attachment=True)

if __name__ == "__main__":
    # 链接本地ip，绑定端口为5000
    app.run(host="0.0.0.0", port=5000)