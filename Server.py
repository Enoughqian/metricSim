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
from flask import session
from tools.checkInput import *
from tools.genDataBaseConfig import *
from tools.checkConfig import *
from tools.calMetric import *
from tools.genPdf import *
from tools.zipFile import *
import shutil
import time
import warnings
warnings.filterwarnings("ignore")

# 构造flask服务
app = Flask(__name__)
# 使用session替代全局变量
app.config['SECRET_KEY'] = os.urandom(24)
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
        date_path = str(datetime.now()).split(" ")[0].replace("-","")
        time_path = str(datetime.now()).split(" ")[1].replace(":", "").split(".")[0]
        
        upload_date_path = os.path.join(basepath, 'uploads/'+date_path)
        upload_time_path = os.path.join(basepath, 'uploads/'+date_path+"/"+time_path)
        
        # 判断日期文件夹是否存在
        if not os.path.exists(upload_date_path):
            os.mkdir(upload_date_path)
        # 判断时间文件夹是否存在
        if not os.path.exists(upload_time_path):
            os.mkdir(upload_time_path)

        # 拼接数据保存路径
        file_path = str(upload_time_path)+"/"+str(f.filename)
        f.save(file_path)
        # 数据读取
        data = pd.read_excel(file_path)
        
        # 数据检查
        judge_result = judgeData(file_path)
        
        # 赋值给session变量
        session['currentpath'] = upload_time_path
        
        # 异常数据删除
        if judge_result[1] != "正常":
            os.remove(file_path)
        else:
            with open(str(upload_time_path)+"/records.txt", "w", encoding="utf-8") as f:
                temp_content = file_path+"\n"+judge_result[0]
                f.write(temp_content)
        return_content = {"数据状态": judge_result[1], "数据频率": judge_result[0]}
    return jsonify(return_content)

# 传入配置信息
@app.route("/config", methods=["POST"])
def form_data():
    # 从session中获取存储的路径
    upload_time_path = session.get('currentpath')
    # 获取前端传过来的信息
    data = request.get_data()
    data = eval(data)
    with open(upload_time_path + "/records.txt", "r", encoding="utf-8") as f:
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
        
        # 配置文件保存
        with open(upload_time_path + "/config.json", "w", encoding="GBK") as f:
            json.dump(data, f, ensure_ascii=False, indent=3)

        # 返回交给前端显示
        return jsonify(data)
    else:
        return jsonify(checkresult[0])

# 点击运行开始计算
@app.route("/calculate", methods=["post"])
def calculate_data():
    start_time = time.time()
    data = request.get_data()
    data = json.loads(eval(data))

    # 从session中获取存储的路径
    upload_time_path = session.get('currentpath')
    
    # 生成sql配置文件
    genDBConfig(data, upload_time_path)

    # 新建结果保存文件夹
    if os.path.exists(upload_time_path+"/result"):
        shutil.rmtree(upload_time_path+"/result")
    os.mkdir(upload_time_path+"/result")
    
    # 开始计算
    sql_config = pd.read_csv(upload_time_path+"/dbconfig.csv")

    # 计算结果和绘图
    cal_result, plot_result = catchDataFromSqlAndCal(data, sql_config)
    cal_result_name = upload_time_path+"/result/sim_result.csv"
    cal_result.to_csv(cal_result_name, index=None, encoding="GBK")

    # 计算耗时
    end_time = time.time()
    print("本次耗时: ", end_time - start_time, "数据数量： ", np.shape(sql_config)[0])
    
    # 绘图数据
    plot_result_name = upload_time_path+"/result/sim_plot.csv"
    plot_result.to_csv(plot_result_name, index=None, encoding="GBK")

    # 绘图
    plot_pages(plot_result_name, plot_result_name[:-4]+".pdf")
    
    # 压缩，增加时间标记，20220907/115353
    upload_time = "-"+ "".join(upload_time_path.split("/")[-2:])
    if os.path.exists(upload_time_path+"/result{}.zip".format(upload_time)):
        os.remove(upload_time_path+"/result{}.zip".format(upload_time))
    print(upload_time_path+"/result{}.zip".format(upload_time))
    make_zip(upload_time_path+"/result", upload_time_path+"/result{}.zip".format(upload_time))
    
    return jsonify({"path": plot_result_name})

# 结果下载
@app.route("/download", methods=["GET"])
def download_file():
    upload_time_path = session.get('currentpath')
    upload_time = "-"+ "".join(upload_time_path.split("/")[-2:])
    name = "result{}.zip".format(upload_time)
    return send_from_directory(upload_time_path, filename = name, as_attachment=True)

if __name__ == "__main__":
    # 链接本地ip，绑定端口为5000
    if os.path.exists("uploads") == False:
        os.mkdir("uploads")
    app.run(host="0.0.0.0", port=5000)