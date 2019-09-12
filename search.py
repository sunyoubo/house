# coding:utf-8
import ast
import time
import argparse
from bs4 import BeautifulSoup
import requests

base_url = 'https://bj.lianjia.com/ditiefang/'
search_condition = 'co21sf1bp100ep250/'
subway_dict = {
    '1号线': 'li647',
    '2号线': 'li648',
    '4号线大兴线': 'li656',
    '5号线': 'li649',
    '6号线': 'li46107350',
    '7号线': 'li46537785',
    '8号线': 'li659',
    '8号线南段': 'li1120037074696977',
    '9号线': 'li43145267',
    '10号线': 'li651',
    '13号线': 'li652',
    '14号线东段': 'li46461179',
    '14号线西段': 'li1110790465974155',
    '15号线': 'li43143633',
    '16号线': 'li1116796246117001',
    '八通线': 'li653',
    '亦庄线': 'li43144847',
    '昌平线': 'li43144993',
    '房山线': 'li43145111',
}

headers = {
    "Host": "bj.lianjia.com",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.186 Safari/537.36"
}


def get_house_by_subway(subway):

    assert subway in subway_dict.values()

    subway_house_list = []
    first_page_url = base_url + subway + '/' + search_condition
    first_page_html = requests.get(first_page_url, headers=headers).text
    soup = BeautifulSoup(first_page_html, "html.parser")
    house_div = soup.find('div', class_='page-box house-lst-page-box')
    if house_div is None:
        return subway_house_list
    page_size_dict = eval(house_div.attrs.get('page-data'))
    page_size = 1
    if isinstance(page_size_dict, dict):
        page_size = page_size_dict.get('totalPage', 1)

    for page in range(1, page_size + 1):
        page_url = base_url + subway + '/pg' + str(page) + search_condition
        page_house_list = get_page_house_list(page_url)
        subway_house_list += list(page_house_list)

    return subway_house_list


def get_page_house_list(page_url):

    response = requests.get(page_url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")
    house_list = soup.find_all('a', {'data-el': 'ershoufang'}, class_='title')
    page_house_list = set()
    for house in house_list:
        page_house_list.add(house.attrs.get('href'))

    return page_house_list


def get_house_detail(house_url):

    response = requests.get(house_url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")
    house_info_div = soup.findAll('div', class_='mainInfo')
    room = ''
    area = 0
    floor = ''
    year = 0
    if len(house_info_div) == 3:
        room = house_info_div[0].contents[0]
        area = float(house_info_div[2].contents[0].replace('平米', ''))

    year_div = soup.findAll('div', class_='subInfo')
    if len(year_div) == 3:
        floor = year_div[0].contents[0]
        year = int(year_div[2].contents[0][:4])

    shoufu_div = soup.find('div', id='calculator')
    if not shoufu_div.attrs.get('data-shoufu'):
        # print("未获取信息：", house_url)
        return {}
    shoufu_data_dict = eval(shoufu_div.attrs.get('data-shoufu').replace('true', 'True').replace('false', 'False'))
    pure_shoufu = shoufu_data_dict.get('pureShoufu', 0)  # 纯首付
    total_shoufu = shoufu_data_dict.get('totalShoufu', 0)  # 总首付
    total_price = int(shoufu_data_dict.get('price', 0))  # 总报价
    evaluation = shoufu_data_dict.get('evaluation', 0)  # 评估价值
    evaluation_rate = (evaluation * 1.0) / total_price  # 评估比例
    month_pay_debx = shoufu_data_dict.get('monthPay', 0)  # 月供-等额本息
    month_pay_debj = shoufu_data_dict.get('monthPayWithInterest', 0)  # 月供-等额本金
    tax_total = 0
    if isinstance(shoufu_data_dict.get('taxResult'), dict):
        tax_total = shoufu_data_dict.get('taxResult', {}).get('taxTotal', 0)  # 总税费

    return dict(pure_shoufu=pure_shoufu, total_shoufu=total_shoufu, total_price=total_price, evaluation=evaluation,
                evaluation_rate=evaluation_rate, month_pay_debx=month_pay_debx, month_pay_debj=month_pay_debj,
                tax_total=tax_total, room=room, area=area, floor=floor, house_age=2019 - year)


def match_house(house_info, shoufu_max, area_min, house_age_max, dixiashi):

    if not dixiashi and house_info.get('floor', '').startswith('地下室'):
        return False

    if shoufu_max*10000 > house_info.get('total_shoufu', 0) > 0:
        if house_info.get('area', 0) > area_min:
            if house_info.get('house_age', 0) < house_age_max:
                return True
    return False


def main(args):

    for subway in subway_dict.items():
        print("地铁：", subway[0])
        subway_house_list = get_house_by_subway(subway[1])
        for house_url in subway_house_list:
            try:
                house_info = get_house_detail(house_url)
            except Exception as e:
                continue
            if match_house(house_info, args.shoufu, args.area, args.age, args.dixiashi):
                print("总首付：", house_info.get('total_shoufu', 0), "详细信息：", house_info, "链接：", house_url)
        time.sleep(5)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='筛选房源条件')

    parser.add_argument('-s', '--shoufu', help='最大首付，单位：万元', default=95, type=int)
    parser.add_argument('-a', '--area', help='最小面积，单位：平方米', default=30, type=int)
    parser.add_argument('-g', '--age', help='最大房龄，单位：年', default=30, type=int)
    parser.add_argument('-d', '--dixiashi', help='是否看半地下室', default=True, type=ast.literal_eval)

    main(parser.parse_args())
