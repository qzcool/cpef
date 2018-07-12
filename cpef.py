import numpy as np
import pandas as pd
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import requests, time, re, math, openpyxl, datetime, os, shutil, psutil, platform, pyautogui, subprocess, webbrowser
from tqdm import *
import xlwings as xw
from selenium import webdriver

from utils import *

# # Basic Definition
# url = 'http://gs.amac.org.cn/amac-infodisc/res/pof/manager/index.html'
# index_m = ['机构诚信信息', '基金管理人全称(中文)', '基金管理人全称(英文)', '登记编号', '组织机构代码', '登记时间',
#        '成立时间', '注册地址', '办公地址', '注册资本(万元)(人民币)', '实缴资本(万元)(人民币)', '企业性质',
#        '注册资本实缴比例', '管理基金主要类别', '申请的其他业务类型', '员工人数', '机构网址', '是否为会员',
#        '法律意见书状态', '律师事务所名称', '律师姓名', '法定代表人/执行事务合伙人(委派代表)姓名', '是否有从业资格',
#        '资格取得方式', '法定代表人/执行事务合伙人(委派代表)工作履历', '高管情况', '暂行办法实施前成立的基金',
#        '暂行办法实施后成立的基金', '机构信息最后更新时间', '特别提示信息', '查询网址/二维码', '存续产品数量',
#        '累计发行产品数量']

# 私募基金URL列表更新：定期运行
def get_cpef_list(save_to_excel=True):
    # chromedriver = "C:\Program Files (x86)\Google\Chrome\Application\chromedriver.exe"
    # os.environ["webdriver.chrome.driver"] = chromedriver
    driver = webdriver.Chrome()#chromedriver)
    driver.get('http://gs.amac.org.cn/amac-infodisc/res/pof/manager/index.html')

    # 等候并点击登录确认
    time.sleep(6)
    driver.find_element_by_xpath("//button[@class='ui-button ui-widget ui-state-default ui-corner-all ui-button-text-only'][@type='button']").click()

    # 生成列表df
    ar = np.array([[],[]])

    # 定义信息爬取函数：重复调取
    def parser(ar):
        # global ar #df
        content = driver.page_source.encode('utf-8')
        soup = BeautifulSoup(content,'lxml')

        table = soup.find('table', attrs={'class':'table table-center dataTable no-footer'})
        table_body = table.find('tbody')

        rows = table_body.find_all('tr')
        for row in rows:
            col_name = row.find_all('td')[1].text.strip()
            col_link = 'http://gs.amac.org.cn/amac-infodisc/res/pof/manager/' + row.find('a')['href'].strip()
            ar = np.append(ar,[[col_name], [col_link]],axis=1)
        return ar

    # 下一页
    def next_page():
        driver.find_element_by_xpath("//a[@class='paginate_button next']").click()

    # 确定页数
    content = driver.page_source.encode('utf-8')
    soup = BeautifulSoup(content,'lxml')
    funds_number = int(soup.find('div',class_='dataTables_info').get_text().split('共')[1].split('条')[0].strip())
    pages_number = int(soup.find('div',class_='dataTables_info').get_text().split('共')[-1].split('页')[0].strip())

    # Append df
    for i in tqdm(range(pages_number)):
        ar = parser(ar) # 要把参数保存下来为ar
        next_page()
        #time.sleep(0.01)

    # Save df
    df = pd.DataFrame({'名称':ar[0],'网址':ar[1]})
    if save_to_excel ==  True:
        df.to_excel('funds_list.xlsx',encoding='gb18030')
    print ('总基金数:',funds_number)


# 基金业协会基金和管理人信息
def get_cpef_fund(url_f):
    headers = {'User-Agent': UserAgent().random}
    r = requests.get(url_f, headers)
    r.encoding = 'utf-8'
    soup = BeautifulSoup(r.text, 'lxml')
    # Any improvements possibility?
    df = pd.DataFrame(columns=['title'])
    df2 = pd.DataFrame(columns=['content'])
    for title in soup.find('table', class_='table table-center table-info').find_all('td', class_='td-title'):
        df = df.append({'title': title.text[:-1]}, ignore_index=True)
    for content in soup.find('table', class_='table table-center table-info').find_all('td', class_='td-content'):
        df2 = df2.append({'content': content.text}, ignore_index=True)
    result_f = pd.concat([df, df2], axis=1).iloc[:-4, ]
    result_f = result_f[result_f['content'] != '']
    result_f = result_f.reset_index(drop=True)
    result_f.loc[len(result_f), 'title'] = '登记网址/二维码'
    result_f.loc[len(result_f) - 1, 'content'] = url_f

    return result_f


# 基金业协会基金和管理人信息
def get_cpef_manager(url_m, tqdm_use=True):
    headers = {'User-Agent': UserAgent().random}
    r = requests.get(url_m, headers)
    r.encoding = 'utf-8'
    soup = BeautifulSoup(r.text, 'lxml')
    # Any improvements possibility?
    df = pd.DataFrame(columns=['title'])
    df2 = pd.DataFrame(columns=['content'])
    for title in soup.find('table', class_='table table-center table-info').find_all('td', class_='td-title'):
        df = df.append({'title': title.text[:-1]}, ignore_index=True)
    for content in soup.find('table', class_='table table-center table-info').find_all('td', class_='td-content'):
        df2 = df2.append({'content': content.text.strip(' &nbsp\r\n')}, ignore_index=True)
    result_m = pd.concat([df, df2], axis=1)
    # result_m = result_m[result_m['content'] != ''] # 可以考虑删除
    result_m = result_m.reset_index(drop=True)
    result_m.loc[len(result_m), 'title'] = '查询网址/二维码'
    result_m.loc[len(result_m) - 1, 'content'] = url_m
    # result_m.content[0] = result_m.content[0].split('\n')[1] # 如果上面删除，下面也要对应调整

    # 存续产品数量
    ## 程序改进：合并dataframe速度提升？
    num3 = 0
    if tqdm_use == True: # 定义是否适用tqdm显示进度
        for fund in tqdm(soup.find_all('a', href=True, class_=False, onclick=False)):
            url = str('http://gs.amac.org.cn/amac-infodisc/res/pof/fund/' + fund['href'].split('/')[2])
            headers = {'User-Agent': str(UserAgent().chrome)}
            r = requests.get(url, headers)
            r.encoding = 'utf-8'
            soup = BeautifulSoup(r.text, 'lxml')
            df = pd.DataFrame(columns=['title'])
            df2 = pd.DataFrame(columns=['content'])
            for title in soup.find('table', class_='table table-center table-info').find_all('td', class_='td-title'):
                df = df.append({'title': title.text[:-1]}, ignore_index=True)
            for content in soup.find('table', class_='table table-center table-info').find_all('td', class_='td-content'):
                df2 = df2.append({'content': content.text}, ignore_index=True)
            result_m_f = pd.concat([df, df2], axis=1).loc[lambda result_m_f: result_m_f['title'] == '运作状态', :]
            if str(result_m_f.content.iloc[0]) == '正在运作':
                num3 += 1
        result_m = result_m.append({'title': '存续产品数量', 'content': num3}, ignore_index=True)

    else:
        for fund in soup.find_all('a', href=True, class_=False, onclick=False):
            url = str('http://gs.amac.org.cn/amac-infodisc/res/pof/fund/' + fund['href'].split('/')[2])
            headers = {'User-Agent': str(UserAgent().chrome)}
            r = requests.get(url, headers)
            r.encoding = 'utf-8'
            soup = BeautifulSoup(r.text, 'lxml')
            df = pd.DataFrame(columns=['title'])
            df2 = pd.DataFrame(columns=['content'])
            for title in soup.find('table', class_='table table-center table-info').find_all('td', class_='td-title'):
                df = df.append({'title': title.text[:-1]}, ignore_index=True)
            for content in soup.find('table', class_='table table-center table-info').find_all('td', class_='td-content'):
                df2 = df2.append({'content': content.text}, ignore_index=True)
            result_m_f = pd.concat([df, df2], axis=1).loc[lambda result_m_f: result_m_f['title'] == '运作状态', :]
            if str(result_m_f.content.iloc[0]) == '正在运作':
                num3 += 1
        result_m = result_m.append({'title': '存续产品数量', 'content': num3}, ignore_index=True)

    # 累计发行产品数量
    num1 = num2 = 0
    try:
        num2 = len(result_m.loc[lambda result_m: result_m['title'] == '暂行办法实施后成立的基金', :].iloc[0, 1].split('月报')) - 1
        num1 = len(result_m.loc[lambda result_m: result_m['title'] == '暂行办法实施前成立的基金', :].iloc[0, 1].split('月报')) - 1
    except Exception as e:
        print (e)
    finally:
        result_m = result_m.append({'title': '累计发行产品数量', 'content': num1 + num2}, ignore_index=True)

    return result_m


# 基金业协会基金和管理人信息: for KYC,从某只产品信息到管理人信息
def kyc_scraper_amac(url_f):
    headers = {'User-Agent': UserAgent().random}
    r = requests.get(url_f, headers)
    r.encoding = 'utf-8'
    soup = BeautifulSoup(r.text, 'lxml')
    # Any improvements possibility?
    df = pd.DataFrame(columns=['title'])
    df2 = pd.DataFrame(columns=['content'])
    for title in soup.find('table', class_='table table-center table-info').find_all('td', class_='td-title'):
        df = df.append({'title': title.text[:-1]}, ignore_index=True)
    for content in soup.find('table', class_='table table-center table-info').find_all('td', class_='td-content'):
        df2 = df2.append({'content': content.text}, ignore_index=True)
    result_f = pd.concat([df, df2], axis=1).iloc[:-4, ]
    result_f = result_f[result_f['content'] != '']
    result_f = result_f.reset_index(drop=True)
    result_f.loc[len(result_f), 'title'] = '登记网址/二维码'
    result_f.loc[len(result_f) - 1, 'content'] = url_f

    # Get manager page url
    url_m = 'http://gs.amac.org.cn/amac-infodisc/res/pof/manager/' + \
            soup.find(href=True, target='blank')['href'].split('/')[-1]
    # Get manager info
    get_cpef_manager(url_m)

    return result_f, result_m


# 基金业协会所有基金管理人的基本信息
## 加入BreakPoint的支持
def get_cpef_info(save_to_excel=True):
    try:
        df = pd.read_excel('funds_list.xlsx', encoding='gb18030')
    except:
        df = get_cpef_list(save_to_excel=True)

    df_info = pd.DataFrame()

    for j in tqdm(range(len(df))):
        result_m = get_cpef_manager(df.网址[j],tqdm_use=False)
        list_manager = []
        for i in range(len(df.columns)):
            list_manager.append([df.columns[i],df.iloc[j].values[i]])
        df_manager = pd.DataFrame(np.concatenate((list_manager, result_m.values), axis=0))
        df_manager.index = df_manager.iloc[:,0]
        df_manager = df_manager.T.drop([0])
        df_info = df_info.append(df_manager,ignore_index=True)
    if save_to_excel == True:
        df_info.to_excel('funds_info.xlsx',encoding='gb18030')

# 每周新增基金统计

# 托管人占比趋势
