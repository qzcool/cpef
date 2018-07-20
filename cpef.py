#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'cpef: tools to help scrap AMAC information 基金业协会私募基金数据库'

__author__ = 'Qiao Zhang'

import numpy as np
import pandas as pd
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import requests, time, re, math, openpyxl, datetime, os, shutil, psutil, platform, pyautogui, subprocess, webbrowser, \
    json
from tqdm import *
import xlwings as xw
from selenium import webdriver
from selenium.webdriver.support.ui import Select
from collections import deque

from utils import *
from decorators import *


class Manager():
    def __init__(self, \
                 # 机构信息
                 manager_url): #\
                 # , manager_nameChinese, manager_nameEnglish, code_registration, code_organization, \
                 # time_registration, time_found_manager, location_registration, location_office, capital_registration, \
                 # capital_paidIn, type_business, type_manager, number_employee, website, \
                 # # 会员信息
                 # membership_status, membership_type, time_membershipEnroll, \
                 # # 法律意见书信息
                 # legalNotice_status, \
                 # # 诚信信息
                 # time_lastUpdated_manager, specialAnnouncement_manager):
        self.manager_url = manager_url
        self.result_m = Manager.get_cpef_manager(manager_url)
        # self.creditInfo = self.result_m.content.iloc[0]
        # self.name_chinese = self.result_m.content.iloc[1]
        # self.name_english = self.result_m.content.iloc[2]
        # self.code_registration = self.result_m.content.iloc[3]
        # self.code_organization = self.result_m.content.iloc[4]
        # self.time_registration = self.result_m.content.iloc[5]
        # self.time_found_manager = self.result_m.content.iloc[6]
        # self.location_registration = self.result_m.content.iloc[7]
        # self.location_office = self.result_m.content.iloc[8]
        # self.capital_registration = self.result_m.content.iloc[9]
        # self.capital_paidIn = self.result_m.content.iloc[10]
        # self.ratio_paidInCapital = self.result_m.content.iloc[12]
        # self.type_business = self.result_m.content.iloc[11]
        # self.type_manager = self.result_m.content.iloc[13]
        # self.number_employee = number_employee
        # self.website = website
        #
        # self.membership_status = membership_status
        # self.membership_type = membership_type
        # self.time_membershipEnroll = time_membershipEnroll
        #
        # self.legalNotice_status = legalNotice_status
        #
        # self.time_lastUpdated_manager = time_lastUpdated_manager
        # self.specialAnnouncement_manager = specialAnnouncement_manager

        # class Membership(Manager):
        #     def __init__(self, membership_status, membership_type, time_membershipEnroll):
        #         self.membership_status = membership_status
        #         self.membership_type = membership_type
        #         self.time_membershipEnroll = time_membershipEnroll

        # class LegalNotice(Manager):
        #     def __init__(self, legalNotice_status):
        #         self.legalNotice_status = legalNotice_status

        # class CreditInfo(Manager):
        #     def __init__(self, time_lastUpdated_manager, specialAnnouncement_manager):
        #         pass

    # 基金业协会单个管理人信息
    ## 准确爬取：产品信息部分/法人工作履历
    @classmethod
    def get_cpef_manager(cls, manager_url, tqdm_use=True):
        """

        :rtype: object
        """
        headers = {'User-Agent': UserAgent().random}
        r = requests.get(manager_url, headers)
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
        result_m.loc[len(result_m) - 1, 'content'] = manager_url
        # result_m.content[0] = result_m.content[0].split('\n')[1] # 如果上面删除，下面也要对应调整
        result_m.content.iloc[1] = result_m.content.iloc[1].split(' &')[0]  # 基金管理人全称(中文)名称修正

        # 产品信息JSON获取
        ## 删除多余的原有两行产品信息
        list_funds = []
        funds_after = soup.find_all('td', class_='td-content')[-3].find_all('p')  ##[0:0:2]
        funds_before = soup.find_all('td', class_='td-content')[-4].find_all('p')  ##[0:0:2]
        for fund_num in range(int(len(funds_after) / 2)):
            fund_name = funds_after[2 * fund_num].get_text().strip()
            fund_url = 'http://gs.amac.org.cn/amac-infodisc/res/pof/' + funds_after[2 * fund_num].find('a')['href'][3:]
            list_funds.append(json.loads(
                json.dumps({'fund_name': fund_name, 'fund_url': fund_url, 'type_fund': 'after'}, sort_keys=True,
                           indent=4)))
        for fund_num in range(int(len(funds_before) / 2)):
            fund_name = funds_before[2 * fund_num].get_text().strip()
            fund_url = 'http://gs.amac.org.cn/amac-infodisc/res/pof/' + funds_before[2 * fund_num].find('a')['href'][3:]
            list_funds.append(json.loads(
                json.dumps({'fund_name': fund_name, 'fund_url': fund_url, 'type_fund': 'before'}, sort_keys=True,
                           indent=4)))
        funds_json = json.loads(json.dumps(list_funds))
        result_m.loc[len(result_m), 'title'] = '产品信息'
        result_m.loc[len(result_m) - 1, 'content'] = funds_json

        # 存续产品数量
        ## 程序改进：合并dataframe速度提升？
        num3 = 0
        if tqdm_use == True:  # 定义是否适用tqdm显示进度
            for fund in tqdm(soup.find_all('a', href=True, class_=False, onclick=False)):
                url = str('http://gs.amac.org.cn/amac-infodisc/res/pof/fund/' + fund['href'].split('/')[2])
                headers = {'User-Agent': str(UserAgent().chrome)}
                r = requests.get(url, headers)
                r.encoding = 'utf-8'
                soup = BeautifulSoup(r.text, 'lxml')
                df = pd.DataFrame(columns=['title'])
                df2 = pd.DataFrame(columns=['content'])
                for title in soup.find('table', class_='table table-center table-info').find_all('td',
                                                                                                 class_='td-title'):
                    df = df.append({'title': title.text[:-1]}, ignore_index=True)
                for content in soup.find('table', class_='table table-center table-info').find_all('td',
                                                                                                   class_='td-content'):
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
                for title in soup.find('table', class_='table table-center table-info').find_all('td',
                                                                                                 class_='td-title'):
                    df = df.append({'title': title.text[:-1]}, ignore_index=True)
                for content in soup.find('table', class_='table table-center table-info').find_all('td',
                                                                                                   class_='td-content'):
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
            print(e)
        finally:
            result_m = result_m.append({'title': '累计发行产品数量', 'content': num1 + num2}, ignore_index=True)

        return result_m

    # 私募基金管理人URL列表更新：定期运行
    @classmethod
    def get_cpef_list_managers(cls, save_to_excel=True):
        driver = webdriver.Chrome()
        driver.get('http://gs.amac.org.cn/amac-infodisc/res/pof/manager/index.html')

        # 等候并点击登录确认
        time.sleep(6)
        driver.find_element_by_xpath(
            "//button[@class='ui-button ui-widget ui-state-default ui-corner-all ui-button-text-only'][@type='button']").click()

        # 生成列表df
        ar = np.array([[], []])

        # 定义信息爬取函数：重复调取
        def parser(ar):
            # global ar #df
            content = driver.page_source.encode('utf-8')
            soup = BeautifulSoup(content, 'lxml')

            table = soup.find('table', attrs={'class': 'table table-center dataTable no-footer'})
            table_body = table.find('tbody')

            rows = table_body.find_all('tr')
            for row in rows:
                col_name = row.find_all('td')[1].text.strip()
                col_link = 'http://gs.amac.org.cn/amac-infodisc/res/pof/manager/' + row.find('a')['href'].strip()
                ar = np.append(ar, [[col_name], [col_link]], axis=1)
            return ar

        # 下一页
        def next_page():
            driver.find_element_by_xpath("//a[@class='paginate_button next']").click()

        # 确定页数
        content = driver.page_source.encode('utf-8')
        soup = BeautifulSoup(content, 'lxml')
        manager_number = int(soup.find('div', class_='dataTables_info').get_text().split('共')[1].split('条')[0].strip())
        pages_number = int(soup.find('div', class_='dataTables_info').get_text().split('共')[-1].split('页')[0].strip())

        # Append df
        for i in tqdm(range(pages_number)):
            ar = parser(ar)  # 要把参数保存下来为ar
            next_page()
            # time.sleep(0.01)

        # Save df
        df = pd.DataFrame({'名称': ar[0], '网址': ar[1]})
        if save_to_excel == True:
            df.to_excel('manager_list.xlsx', encoding='gb18030')
        print('总基金数:', manager_number)


class Custodian():
    def __init__(self, custodian_name, custodian_foundDate, custodian_rank):
        self.custodian_name = custodian_name
        self.custodian_foundDate = custodian_foundDate
        self.custodian_rank = custodian_rank


class Executive(Manager):
    def __init__(self, legalEntity_name, legalEntity_charteredStatus):
        self.legalEntity_name = legalEntity_name
        self.legalEntity_charteredStatus = legalEntity_charteredStatus


class Fund(Manager, Custodian):
    def __init__(self, fund_url):
                 # , fund_name, fund_code, time_found_fund, time_registration_fund, registration_stage, \
                 # type_fund, type_currency, manager_nameChinese, type_management, custodian_name, \
                 # operation_status, time_lastUpdated_fund, specialAnnouncement_fund, information_reveal):
        # information_reveal为json
        self.fund_url = fund_url
        self.result_f = Fund.get_cpef_fund(fund_url)
        # self.fund_name = fund_name
        # self.fund_code = fund_code
        # self.time_found_fund = time_found_fund
        # self.time_registration_fund = time_registration_fund
        # self.registration_stage = registration_stage
        # self.type_fund = type_fund
        # self.type_currency = type_currency
        # self.manager_nameChinese = super().__init__(manager_nameChinese)
        # self.type_management = type_management
        # self.custodian_name = super().__init__(custodian_name)
        # self.operation_status = operation_status
        # self.time_lastUpdated_fund = time_lastUpdated_fund
        # self.specialAnnouncement_fund = specialAnnouncement_fund
        # self.information_reveal = information_reveal

    # 私募基金产品URL列表更新：定期运行
    ## tqdm显示错误，无法合并显示进度是为什么？
    @classmethod
    def get_cpef_list_funds(cls, save_to_csv=True, open_only=False):
        """
        私募基金产品URL列表更新：定期运行
        :param save_to_csv: 声明是否保存为csv，之所以不为xlsx格式是因为xlsx不能超过63565行
        :return:  None
        """

        # 打开待爬取网页
        def open_funds_list():
            driver = webdriver.Chrome()
            driver.get('http://gs.amac.org.cn/amac-infodisc/res/pof/fund/index.html')
            # 等候并点击登录确认
            time.sleep(6)
            driver.find_element_by_xpath(
                "//button[@class='ui-button ui-widget ui-state-default ui-corner-all ui-button-text-only'][@type='button']").click()
            return driver

        # 定义函数：加快爬取速度,修改单页最大显示行数和将运作状态设置为“正在运作”
        def page_manipulator(driver, open_only):
            if open_only == True:
                driver.find_element_by_link_text(u"正在运作").click()
                driver.find_element_by_xpath(u"//input[@value='查询']").click()
            driver.find_element_by_name("fundlist_length").click()
            Select(driver.find_element_by_name("fundlist_length")).select_by_visible_text("100")
            driver.find_element_by_name("fundlist_length").click()
            return driver

        # 确定页数
        def count_pages(driver):
            content = driver.page_source.encode('utf-8')
            soup = BeautifulSoup(content, 'lxml')
            funds_number = int(
                soup.find('div', class_='dataTables_info').get_text().split('共')[1].split('条')[0].strip())
            pages_number = int(
                soup.find('div', class_='dataTables_info').get_text().split('共')[-1].split('页')[0].strip())
            return funds_number, pages_number

        # 定义函数：信息爬取,可重复调取
        def parser(d):  # ar):
            content = driver.page_source.encode('utf-8')
            soup = BeautifulSoup(content, 'lxml')
            table = soup.find('table', attrs={'class': 'table table-center dataTable no-footer'})
            table_body = table.find('tbody')
            rows = table_body.find_all('tr')
            for row in rows:
                col_fund_name = row.find_all('td')[1].text.strip()
                col_fund_url = 'http://gs.amac.org.cn/amac-infodisc/res/pof/fund/' + row.find_all('td')[1].find('a')[
                    'href'].strip()
                col_manager = row.find_all('td')[2].text.strip()
                col_manager_url = 'http://gs.amac.org.cn/amac-infodisc/res/pof/' + row.find_all('td')[2].find('a')[
                                                                                       'href'].strip()[3:]
                col_custodian = row.find_all('td')[3].text.strip()
                col_date_founding = row.find_all('td')[4].text.strip()
                col_date_register = row.find_all('td')[5].text.strip()
                # col_fund_status = get_cpef_fund_status(col_fund_url)
                d.append([col_fund_name, col_fund_url, col_manager, col_manager_url, col_custodian, col_date_founding,
                          col_date_register])  # , col_fund_status])
                # ar = np.append(ar,[[col_fund_name], [col_fund_url], [col_manager], [col_manager_url], [col_custodian], [col_date_founding], [col_date_register]],axis=1)
            return d  # ar

        # 翻页
        def next_page():
            driver.find_element_by_link_text(u"下一页").click()

        # 生成列表df
        d = deque()
        # ar = np.array()#[[],[],[],[],[],[],[]]) ## 是否可以不声明？
        # 打开待爬取网页
        driver = open_funds_list()
        # 修改单页最大显示行数
        driver = page_manipulator(driver, open_only)
        time.sleep(3)
        # 确定页数
        funds_number, pages_number = count_pages(driver)
        # Append df
        for i in tqdm(range(pages_number)):
            d = parser(d)  # 要把参数保存下来为ar
            next_page()
            # time.sleep(0.01)
        # Save df
        # df = pd.DataFrame({'基金名称':ar[0],'基金网址':ar[1], '私募基金管理人名称':ar[2], '私募基金管理人网址':ar[3], '托管人名称':ar[4], '成立时间':ar[5], '备案时间':ar[6]})
        df = pd.DataFrame(
            {'基金名称': [item[0] for item in d], '基金网址': [item[1] for item in d], '私募基金管理人名称': [item[2] for item in d],
             '私募基金管理人网址': [item[3] for item in d], '托管人名称': [item[4] for item in d], '成立时间': [item[5] for item in d],
             '备案时间': [item[6] for item in d]})  # , '基金运作状态':[item[7] for item in d]})
        if save_to_csv == True:
            if open_only == True:
                file_name = 'funds_list_open.csv'
            else:
                file_name = 'funds_list.csv'
            df.to_csv(file_name, encoding='gb18030')
        print('总基金数:', funds_number)

        return df

    # 查询单只基金：全部信息
    ## 允许子查询：只查询需要的字段比如‘运作状态’
    # @logger
    # @timer
    @classmethod
    def get_cpef_fund(cls, fund_url):
        headers = {'User-Agent': UserAgent().random}
        r = requests.get(fund_url, headers)
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.text, 'lxml')
        ## Any improvements possibility?
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
        result_f.loc[len(result_f) - 1, 'content'] = fund_url

        return result_f

    # 查询单子基金信息：运作状态
    @classmethod
    def get_cpef_fund_status(cls, fund_url):
        headers = {'User-Agent': UserAgent().random}
        r = requests.get(fund_url, headers)
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.text, 'lxml')
        return soup.find('td', text='运作状态:').findNext('td').text

##############################################################################
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
        df = pd.read_excel('manager_list.xlsx', encoding='gb18030')
    except:
        df = get_cpef_list(save_to_excel=True)

    df_info = pd.DataFrame()

    for j in tqdm(range(len(df))):
        result_m = get_cpef_manager(df.网址[j], tqdm_use=False)
        list_manager = []
        for i in range(len(df.columns)):
            list_manager.append([df.columns[i], df.iloc[j].values[i]])
        df_manager = pd.DataFrame(np.concatenate((list_manager, result_m.values), axis=0))
        df_manager.index = df_manager.iloc[:, 0]
        df_manager = df_manager.T.drop([0])
        df_info = df_info.append(df_manager, ignore_index=True)
    if save_to_excel == True:
        df_info.to_excel('funds_info.xlsx', encoding='gb18030')

##############################################################################

# 每周新增基金统计

# 托管人占比趋势
