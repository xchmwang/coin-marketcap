from bs4 import BeautifulSoup
import json, time, threading
import utils
from mysql_tables import db, Trading_pair
from sqlalchemy import func
from sqlalchemy.sql import label

from utils import logger


def get_token_trading_pairs(url, token):
    time.sleep(3)
    logger.info(url)
    l = list()
    soup = utils.get_soup_by_url(url)
    records = soup.find(
        'table', id='markets-table').find('tbody').find_all('tr')
    for record in records:
        fields = record.find_all('td')
        rank = fields[0].text.replace('\n', '')
        source = fields[1].text.replace('\n', '')
        pair = fields[2].text.replace('\n', '')
        volume = fields[3].text.replace('\n', '').replace(',', '').replace(
            '$', '').replace(' ', '').replace('*', '')
        price = fields[4].text.replace('\n', '').replace(',', '').replace(
            '$', '').replace(' ', '').replace('*', '')
        percent = fields[5].text.replace('\n', '').replace(' ', '')
        date = time.strftime("%Y%m%d", time.gmtime())

        if float(percent.replace('%', '')) == 0:
            continue

        d = {
            'token': token,
            'date': date,
            'rank': rank,
            'source': source,
            'pair': pair,
            'volume': volume,
            'price': price,
            'percent': percent
        }
        # print json.dumps(d)
        l.append(d)

    # print len(l)
    return l


def get_all_tokens_trading_pairs():
    token_names = utils.get_token_names()
    if 'nebulas-token' not in token_names:
        token_names.append('nebulas-token')

    url = 'https://coinmarketcap.com'
    all_tokens_trading_pairs = list()
    for token in token_names:
        pair_url = url + '/currencies/' + token + '/#markets'
        l = get_token_trading_pairs(pair_url, token)
        all_tokens_trading_pairs.append(l)

    return all_tokens_trading_pairs


def write_trading_pairs_to_db():
    all_tokens_trading_pairs = get_all_tokens_trading_pairs()
    logger.info('done with get all tokens trading pairs')
    for trading_pairs in all_tokens_trading_pairs:
        for record in trading_pairs:
            token = record['token']
            date = record['date']
            rank = int(record['rank'])
            source = record['source']
            pair = record['pair']
            volume = int(record['volume'])
            price = float(record['price'])
            percent = float(record['percent'].replace('%', ''))

            trading_pair = Trading_pair(
                token=token,
                date=date,
                rank=rank,
                source=source,
                pair=pair,
                volume=volume,
                price=price,
                percent=percent)
            db.session.add(trading_pair)
            db.session.commit()
            # print 'done with record:', record

    global timer
    timer = threading.Timer(24 * 60 * 60, write_trading_pairs_to_db)
    timer.start()
    return


def pair_history_sum_json_to_csv(rows):
    csv_str = 'rank,pair,volume\n'
    for r in rows:
        csv_str += (str(r['rank']) + ',')
        csv_str += (str(r['pair']) + ',')
        csv_str += (str(r['volume']) + '\n')
    return csv_str


def read_trading_pairs_sum_from_db(start_date, end_date, token='all', topk=5):
    if token == 'all':
        base_query = db.session.query(
            Trading_pair.pair,
            label('total_volume', func.sum(Trading_pair.volume))).filter(
                Trading_pair.date >= start_date).filter(
                    Trading_pair.date <= end_date).group_by(
                        Trading_pair.pair).order_by(
                            func.sum(Trading_pair.volume).desc()).all()
    else:
        base_query = db.session.query(
            Trading_pair.pair,
            label('total_volume', func.sum(Trading_pair.volume))).filter(
                Trading_pair.date >= start_date).filter(
                    Trading_pair.date <= end_date).filter(
                        Trading_pair.token == token).group_by(
                            Trading_pair.pair).order_by(
                                func.sum(Trading_pair.volume).desc()).all()

    l = list()
    rank = 1
    for res in base_query:
        d = {'rank': rank, 'pair': res.pair, 'volume': res.total_volume}
        rank = rank + 1
        l.append(d)

        if len(l) == topk:
            break

    return l


def date_format(date):
    date = str(date)
    return date[:4] + '/' + date[4:6] + '/' + date[6:]


def read_trading_pair_from_db_with_topk(start_date, end_date, token='all', topk=5):
    if token == 'all':
        base_query = db.session.query(
            Trading_pair).filter(
                Trading_pair.date >= start_date).filter(
                    Trading_pair.date <= end_date).filter(
                        Trading_pair.rank <= topk).order_by(
                            Trading_pair.rank, Trading_pair.date).all()
    else:
        base_query = db.session.query(
            Trading_pair).filter(
                Trading_pair.date >= start_date).filter(
                    Trading_pair.date <= end_date).filter(
                        Trading_pair.token == token).filter(
                            Trading_pair.rank <= topk).order_by(
                                Trading_pair.rank, Trading_pair.date).all()

    l = list()
    for res in base_query:
        d = {
            'date': date_format(res.date),
            'rank': res.rank,
            'source': res.source,
            'pair': res.pair,
            'volume': res.volume,
            'price': res.price,
            'percent': res.percent
        }
        l.append(d)
    return l


def read_trading_pair_from_db_with_k(start_date, end_date, token='all', k=1):
    if token == 'all':
        base_query = db.session.query(
            Trading_pair).filter(
                Trading_pair.date >= start_date).filter(
                    Trading_pair.date <= end_date).filter(
                        Trading_pair.rank == k).all()
    else:
        base_query = db.session.query(
            Trading_pair).filter(
                Trading_pair.date >= start_date).filter(
                    Trading_pair.date <= end_date).filter(
                        Trading_pair.token == token).filter(
                            Trading_pair.rank == k).all()

    l = list()
    for res in base_query:
        d = {
            'date': date_format(res.date),
            'rank': res.rank,
            'source': res.source,
            'pair': res.pair,
            'volume': res.volume,
            'price': res.price,
            'percent': res.percent
        }
        l.append(d)
    return l


def pair_history_json_to_csv(rows):
    csv_str = 'date,rank,source,pair,volume,price,percent\n'
    for r in rows:
        csv_str += (str(r['date']) + ',')
        csv_str += (str(r['rank']) + ',')
        csv_str += (str(r['source']) + ',')
        csv_str += (str(r['pair']) + ',')
        csv_str += (str(r['volume']) + ',')
        csv_str += (str(r['price']) + ',')
        csv_str += (str(r['percent']) + '\n')
    return csv_str

