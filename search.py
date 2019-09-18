# coding:utf-8
import ast
import time
import argparse
from bs4 import BeautifulSoup
import requests
import json

base_url = 'https://bj.lianjia.com/ditiefang/'
api_url = 'https://bj.lianjia.com/tools/calccost?house_code='
search_condition = 'co21sf1bp100ep250/'
subway_dict = {
    'li647': '1号线',
    'li648': '2号线',
    'li656': '4号线大兴线',
    'li649': '5号线',
    'li46107350': '6号线',
    'li46537785': '7号线',
    'li659': '8号线',
    'li1120037074696977': '8号线南段',
    'li43145267': '9号线',
    'li651': '10号线',
    'li652': '13号线',
    'li46461179': '14号线东段',
    'li1110790465974155': '14号线西段',
    'li43143633': '15号线',
    'li1116796246117001': '16号线',
    'li653': '八通线',
    'li43144847': '亦庄线',
    'li43144993': '昌平线',
    'li43145111': '房山线',
}

line_order = ['li652', 'li659', 'li649', 'li648', 'li647', 'li651', 'li656', 'li43145267', 'li46107350', 'li43143633',
              'li1116796246117001', 'li46537785', 'li1120037074696977', 'li46461179', 'li1110790465974155',
              'li43144993', 'li653', 'li43144847', 'li43145111']

headers = {
    "Host": "bj.lianjia.com",
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.186 "
                  "Safari/537.36"
}


def get_house_by_subway(subway):
    assert subway in subway_dict.keys()

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


def get_house_detail_by_api(house_url):
    assert house_url.endswith('.html')

    room, area, floor, year = get_house_base(house_url)
    house_info = dict(room=room, area=area, floor=floor, house_age=2019 - year)
    house_code = house_url.split('/')[-1].split('.')[0]
    url = api_url + house_code
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        content = json.loads(response.content.decode(encoding="utf-8"))
        if not content.get("errorCode") == 0:
            return False, house_info
        data = content.get('data', {})
        pure_shoufu = data.get('payment', {}).get('cost_house', 0)
        tax_total = data.get('payment', {}).get('cost_tax', 0)
        cost_jingjiren = data.get('payment', {}).get('cost_jingjiren', 0)
        total_shoufu = pure_shoufu + tax_total + cost_jingjiren
        total_price = data.get('params', {}).get('price_listing')
        evaluation = data.get('params', {}).get('wang_qian_price', 0)
        evaluation_rate = '%.2f' % ((evaluation * 1.0) / total_price)
        month_pay_debx = data.get('payment', {}).get('loan_info', {}).get('elp', {}).get('mp', 0)
        month_pay_debj = data.get('payment', {}).get('loan_info', {}).get('epp', {}).get('mp', 0)
        house_info.update(dict(pure_shoufu=pure_shoufu, total_shoufu=total_shoufu, total_price=total_price,
                               evaluation=evaluation, evaluation_rate=evaluation_rate, month_pay_debx=month_pay_debx,
                               month_pay_debj=month_pay_debj, tax_total=tax_total, cost_jingjiren=cost_jingjiren))

    return True, house_info


def get_house_detail_by_html(house_url):
    response = requests.get(house_url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")
    room, area, floor, year = get_house_base(house_url)

    shoufu_div = soup.find('div', id='calculator')
    if not shoufu_div.attrs.get('data-shoufu'):
        print("未获取信息：", house_url)
        return {}
    shoufu_data_dict = eval(shoufu_div.attrs.get('data-shoufu').replace('true', 'True').replace('false', 'False'))
    pure_shoufu = shoufu_data_dict.get('pureShoufu', 0)  # 纯首付
    total_shoufu = shoufu_data_dict.get('totalShoufu', 0)  # 总首付
    total_price = int(shoufu_data_dict.get('price', 0))  # 总报价
    evaluation = shoufu_data_dict.get('evaluation', 0)  # 评估价值
    evaluation_rate = '%.2f' % ((evaluation * 1.0) / total_price)  # 评估比例
    month_pay_debx = shoufu_data_dict.get('monthPay', 0)  # 月供-等额本息
    month_pay_debj = shoufu_data_dict.get('monthPayWithInterest', 0)  # 月供-等额本金
    tax_total = 0
    if isinstance(shoufu_data_dict.get('taxResult'), dict):
        tax_total = shoufu_data_dict.get('taxResult', {}).get('taxTotal', 0)  # 总税费

    return dict(pure_shoufu=pure_shoufu, total_shoufu=total_shoufu / 10000, total_price=total_price / 10000,
                evaluation=evaluation, evaluation_rate=evaluation_rate, month_pay_debx=month_pay_debx,
                month_pay_debj=month_pay_debj, tax_total=tax_total, room=room, area=area,
                floor=floor, house_age=2019 - year)


def get_house_base(house_url):
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
        try:
            year = int(year_div[2].contents[0][:4])
        except:
            year = 2019

    return room, area, floor, year


def match_house(house_info, shoufu_max, area_min, house_age_max, dixiashi):
    if not dixiashi and house_info.get('floor', '').startswith('地下室'):
        return False

    if shoufu_max > house_info.get('total_shoufu', 0) > 0:
        if house_info.get('area', 0) > area_min:
            if house_info.get('house_age', 0) < house_age_max:
                return True
    return False


def main(args):
    file_name = time.strftime("%Y-%m-%d_%H_%M", time.localtime())
    house_count = 0
    all_total_shoufu = 0
    all_total_price = 0
    match_house_list = []

    with open('history/' + file_name + '.txt', 'w') as f:
        f.write("筛选条件：" + str(args) + '\n')
        f.write('\n')
        for subway in line_order:
            print("地铁：", subway_dict[subway])
            subway_house_list = get_house_by_subway(subway)
            for house_url in subway_house_list:
                if house_url in match_house_list:
                    continue
                try:
                    result, house_info = get_house_detail_by_api(house_url)
                    if not result:
                        house_info = get_house_detail_by_html(house_url)
                    time.sleep(1)
                except Exception as e:
                    continue
                if match_house(house_info, args.shoufu, args.area, args.age, args.dixiashi):
                    match_house_list.append(house_url)
                    house_count += 1
                    all_total_shoufu += house_info.get('total_shoufu', 0)
                    all_total_price += house_info.get('total_price', 0)
                    out_put = "地铁：" + subway_dict[subway] + " 总首付（万）：" + str(
                        int(house_info.get('total_shoufu', 0))) + " 详细信息：" \
                              + str(house_info) + " 链接：" + house_url
                    print('房源匹配 --->' + out_put + " 链接：" + house_url)
                    f.write(out_put + '\n')
                else:
                    print("房源未匹配 总首付（万)：", str(int(house_info.get('total_shoufu', 0))), house_info, " 链接：" + house_url)
            time.sleep(3)

        f.write('\n')
        f.write("总房源数：" + str(house_count) + '\n')
        f.write("均首付：" + str(all_total_shoufu / house_count) + '\n')
        f.write("均总价：" + str(all_total_price / house_count) + '\n')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='筛选房源条件')

    parser.add_argument('-s', '--shoufu', help='最大首付，单位：万元', default=95, type=int)
    parser.add_argument('-a', '--area', help='最小面积，单位：平方米', default=30, type=int)
    parser.add_argument('-g', '--age', help='最大房龄，单位：年', default=30, type=int)
    parser.add_argument('-d', '--dixiashi', help='是否看半地下室', default=True, type=ast.literal_eval)

    main(parser.parse_args())
