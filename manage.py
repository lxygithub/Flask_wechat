import json

from flask import Flask, request, render_template, session, jsonify
import time
import requests
import re
from xmlparser import parse

app = Flask(__name__)
app.debug = True
app.secret_key = "fdsfsdfs"
if __name__ == '__main__':
    app.run()


@app.route("/")
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        ctime = str((int)(time.time() * 1000))
        qcode_url = "https://login.wx.qq.com/jslogin?appid=wx782c26e4c19acffb&redirect_uri=https%3A%2F%2Fwx.qq.com%2Fcgi-bin%2Fmmwebwx-bin%2Fwebwxnewloginpage&fun=new&lang=zh_&_={0}".format(
            ctime)
        ret = requests.get(qcode_url)
        qcode = re.findall('uuid = "(.*)";', ret.text)[0]
        session["qcode"] = qcode
        return render_template("login.html", qcode=qcode)
    else:
        pass


@app.route("/check_login", methods=["GET", "POST"])
def check_login():
    response = {"code": 408}
    ctime = str((int)(time.time() * 1000))
    qcode = session.get("qcode")
    check_url = "https://login.wx.qq.com/cgi-bin/mmwebwx-bin/login?loginicon=true&uuid={0}&tip=0&r=-2023176346&_={1}".format(
        qcode, ctime)
    resp = requests.get(check_url)
    ret = resp.text
    # time.sleep(10)
    if "code=201" in ret:  # 已经扫码
        list_src = re.findall("userAvatar = '(.*)';", ret)
        if len(list_src) > 0:
            src = list_src[0]
        else:
            src = "没有头像"
        response["code"] = 201
        response["src"] = src
    elif "code=200" in ret:  # 已经确认登录
        response["code"] = 200
        redirect_uri = re.findall('redirect_uri="(.*)";', ret)[0]
        session["login_cookie"] = resp.cookies.get_dict()

        # 向redirect_uri地址发送请求，获取凭证相关信息
        redirect_uri = redirect_uri + "&fun=new&version=v2"
        ret = requests.get(redirect_uri)
        ticket_ret = ret.text
        ticket_dict = parse(ticket_ret)
        session["ticket_dict"] = ticket_dict
        session["ticket_cookie"] = ret.cookies.get_dict()
        response["code"] = 200
    return jsonify(response)


@app.route("/index")
def index():
    ticket_dict = session.get("ticket_dict")
    # 用户数据初始化
    init_url = "https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxinit?r=-2039546931&pass_ticket={0}".format(
        ticket_dict.get("pass_ticket"))
    data_dict = {"BaseRequest":
                     {"Uin": ticket_dict.get("wxuin"),
                      "Sid": ticket_dict.get("wxsid"),
                      "Skey": ticket_dict.get("skey"),
                      "DeviceID": "e425567187234790"}}
    init_ret = requests.post(
        url=init_url,
        json=data_dict,
    )
    init_ret.encoding = "utf-8"
    init_json = init_ret.json()

    user_dict = init_json["User"]
    sync_key = init_json["SyncKey"]
    session["current_user"] = user_dict
    session["sync_key"] = sync_key

    return render_template("index.html", init_json=init_json)


@app.route('/get_img')
def get_img():
    # 获取头像
    ticket_cookie = session.get("ticket_cookie")
    head_url = "https://wx.qq.com" + session["current_user"]["HeadImgUrl"]
    img_ret = requests.get(head_url, cookies=ticket_cookie,
                           headers={"Content-Type": "image/jpeg"})
    return img_ret.content


@app.route('/user_list')
def user_list():
    ctime = str((int)(time.time() * 1000))
    if "'ret': '1203'" in str(session["ticket_dict"]):
        return render_template("send.html", error="新注册的微信账号无法使用web版本微信")
    else:
        skey = session["ticket_dict"]["skey"]
        if not skey:
            skey = ""
        user_list_url = "https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxgetcontact?lang=zh_&r={0}&seq=0&skey={1}".format(
            ctime, skey)
        ticket_cookie = session.get("ticket_cookie")
        ret = requests.get(url=user_list_url, cookies=ticket_cookie)
        ret.encoding = "utf-8"
        wx_user_dict = ret.json()
        return render_template("user_list.html", wx_user_dict=wx_user_dict)


@app.route('/send/<username>/<nickname>', methods=["GET", "POST"])
def send(username, nickname):
    current_user = session["current_user"]
    from_user = current_user["UserName"]
    content = request.form.get('user_msg', "")
    ctime = str((int)(time.time() * 1000))
    ticket_dict = session.get("ticket_dict")
    data_dict = {
        "BaseRequest":
            {"Uin": ticket_dict.get("wxuin"),
             "Sid": ticket_dict.get("wxsid"),
             "Skey": ticket_dict.get("skey"),
             "DeviceID": "e425567187234790"},
        "Msg": {
            "ClientMsgId": ctime,
            "Content": content,
            "FromUserName": from_user,
            "LocalID": ctime,
            "ToUserName": username,
            "Type": 1},
        "Scene": 0}
    send_url = "https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxsendmsg?lang=zh_&pass_ticket={0}".format(
        ticket_dict.get("pass_ticket"))
    ret = requests.post(url=send_url,
                        data=bytes(json.dumps(data_dict, ensure_ascii=False), encoding="utf-8")
                        # 防止出现Unicode码
                        )
    return render_template("send.html", username=username, nickname=nickname, ret=ret.text)


@app.route('/get_msg')
def get_msg():
    # time.sleep(10)
    sync_data_list = []
    sync_key = session["sync_key"]["List"]
    for item in sync_key:
        temp = "%s_%s" % (item['Key'], item['Val'])
        sync_data_list.append(temp)
    sync_data_str = "|".join(sync_data_list)
    nid = str(int(time.time() * 1000))
    ticket_dict = session.get("ticket_dict")
    ticket_cookie = session.get("ticket_cookie")
    sync_dict = {
        "r": nid,
        "skey": ticket_dict['skey'],
        "sid": ticket_dict['wxsid'],
        "uin": ticket_dict['wxuin'],
        "deviceid": "e531777446530354",
        "synckey": sync_data_str
    }
    sync_url = "https://webpush.wx.qq.com/cgi-bin/mmwebwx-bin/synccheck"
    all_cookie = {}
    all_cookie.update(session["login_cookie"])
    all_cookie.update(ticket_cookie)
    ret = requests.get(url=sync_url, params=sync_dict, cookies=all_cookie)
    msg_list = []
    if 'selector:"2"' in ret.text:  # 有新消息
        fetch_msg_url = "https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxsync?sid={0}&skey={1}&lang=zh_CN&pass_ticket={2}".format(
            ticket_dict['wxsid'], ticket_dict['skey'], ticket_dict['pass_ticket'])

        data_dict = {
            "BaseRequest": {
                "Uin": ticket_dict["wxuin"],
                "Sid": ticket_dict["wxsid"],
                "Skey": ticket_dict["skey"],
                "DeviceID": "e425567187234790"
            },
            "SyncKey": session["sync_key"],
            "rr": nid}
        ret_fetch_msg = requests.post(fetch_msg_url, json=data_dict)
        ret_fetch_msg.encoding = 'utf-8'
        ret_fetch_msg_dict = json.loads(ret_fetch_msg.text)
        session["sync_key"] = ret_fetch_msg_dict['SyncKey']  # 更新sync

        for item in ret_fetch_msg_dict['AddMsgList']:
            msg_list.append(item)
            print("{0}  对  {1}说:-->{2}".format(item['FromUserName'], item['ToUserName'],
                                               item['Content']))
    return render_template("send.html", msg_lislt=msg_list)
