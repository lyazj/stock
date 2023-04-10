#!/usr/bin/env python3

import requests
import anti_useragent as ai
import json
import numpy as np
import pandas as pd
import datetime

LOW = 0
OPEN = 1
HIGH = 2
CLOSE = 3

ua = ai.UserAgent('windows')
session = requests.session()

class HTTPError(RuntimeError):
    pass

def get(url: str):
    print('get:', url)
    res = session.get(url)
    print(res)
    if not res.ok: raise HTTPError(res.status_code)
    return res.text

def parse_data(js_content: str):
    js_content = js_content.strip()
    cp_pos = -1
    assert js_content[cp_pos] == ')'
    op_pos = js_content.find('(')
    assert op_pos != -1
    json_content = js_content[op_pos + 1 : cp_pos]
    data = json.loads(json_content)
    assert data['priceFactor'] == 100
    name = data['name']
    price = np.array(data['price'].split(','), dtype='int')
    price = price.reshape(price.shape[0] // 4, 4)
    price[:,1:] += price[:,:1]
    sortYear = data['sortYear']
    sortYear = sum([[str(y)] * c for (y, c) in sortYear], [])
    dates = data['dates'].split(',')
    dates = [y + '-' +  md[:2] + '-' + md[2:] + ' 15:00' for (y, md) in zip(sortYear, dates, strict=True)]
    dates = np.array(dates, dtype='datetime64')
    return name, price, dates

success = open('success.txt', 'a')
failed = open('failed.txt', 'a')
print(datetime.datetime.now(), file=failed)
discarded = open('discarded.txt', 'a')

def fetch_and_save(code: str):
    print('working:', code)
    for _ in range(5):
        try:
            session.cookies.clear()
            session.headers['User-Agent'] = ua.chrome
            data = get(f'https://d.10jqka.com.cn/v6/line/hs_{code}/01/all.js')
            name, price, dates = parse_data(data)
            rise = (price[1:,CLOSE] - price[:-1,CLOSE]) / price[:-1,CLOSE]
            dates = dates[1:]
            dframe = pd.DataFrame({
                '时间': dates,
                '收价（分）': price[1:,CLOSE],
                '涨幅': rise,
            })
            dframe.to_excel(f'{code}-{name}.xlsx', index=False)
            print(code, file=success)
            print('success:', code)
            break
        except HTTPError as e:
            if e.args[0] == 404:
                print(code, file=discarded)
                print('discarding:', code)
                break
        except Exception:
            pass
    else:
        print(code, file=failed)
        print('failed:', code)

if __name__ == '__main__':
    codes = open('codes.txt').read().strip().split('\n')
    try:
        success_codes = open('success.txt').read().strip().split('\n')
    except FileNotFoundError:
        success_codes = []
    try:
        discarded_codes = open('discarded.txt').read().strip().split('\n')
    except FileNotFoundError:
        discarded_codes = []
    for code in codes:
        if code in success_codes:
            # print('skipping:', code)
            continue
        if code in discarded_codes:
            # print('skipping:', code)
            continue
        fetch_and_save(code)
