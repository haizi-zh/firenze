# coding=utf-8
import json
import string
import re
import common as cm
import geosense as gs

__author__ = 'Zephyre'

db = None
log_name = 'mulberry_log.txt'


def fetch_stores(data):
    url = data['url']
    try:
        body = cm.get_data(url)
    except Exception, e:
        cm.dump('Error in fetching stores: %s' % url, log_name)
        return []

    store_list = []
    for m1 in re.finditer(ur'<country id="[^"]+">', body):
        country_sub = cm.extract_closure(body[m1.start():], ur'<country\b', ur'</country>')[0]
        m = re.search(ur'<name><!\[CDATA\[(.+?)\]\]></name>', country_sub)
        if m is None:
            continue
        country = m.group(1).strip().upper()
        for m2 in re.finditer(ur'<city id="[^"]+">', country_sub):
            city_sub = cm.extract_closure(country_sub[m2.start():], ur'<city\b', ur'</city>')[0]
            m = re.search(ur'<name><!\[CDATA\[(.+?)\]\]></name>', city_sub)
            if m is None:
                continue
            city = m.group(1).strip().upper()
            for m3 in re.finditer(ur'<store id="[^"]+"', city_sub):
                entry = cm.init_store_entry(data['brand_id'], data['brandname_e'], data['brandname_c'])
                entry[cm.country_e] = country
                entry[cm.city_e] = city

                store_sub = cm.extract_closure(city_sub[m3.start():], ur'<store\b', ur'</store>')[0]
                m = re.search(ur'lat="(-?\d+\.\d+)"', store_sub)
                if m is not None:
                    entry[cm.lat] = string.atof(m.group(1))
                m = re.search(ur'long="(-?\d+\.\d+)"', store_sub)
                if m is not None:
                    entry[cm.lng] = string.atof(m.group(1))
                m = re.search(ur'<name><!\[CDATA\[(.+?)\]\]></name>', store_sub)
                if m is not None:
                    entry[cm.name_e] = m.group(1).strip()
                m = re.search(ur'<telephone><!\[CDATA\[(.+?)\]\]></telephone>', store_sub)
                if m is not None:
                    entry[cm.tel] = m.group(1).strip()
                m = re.search(ur'<stock><!\[CDATA\[(.+?)\]\]></stock>', store_sub)
                if m is not None:
                    entry[cm.store_type] = m.group(1).strip()
                entry[cm.addr_e] = ', '.join([entry[tmp] for tmp in [cm.name_e, cm.city_e, cm.country_e]])

                gs.field_sense(entry)
                ret = gs.addr_sense(entry[cm.addr_e], entry[cm.country_e])
                if ret[1] is not None and entry[cm.province_e] == '':
                    entry[cm.province_e] = ret[1]
                gs.field_sense(entry)

                cm.dump('(%s / %d) Found store: %s, %s (%s, %s)' % (data['brandname_e'], data['brand_id'],
                                                                    entry[cm.name_e], entry[cm.addr_e],
                                                                    entry[cm.country_e],
                                                                    entry[cm.continent_e]), log_name)
                db.insert_record(entry, 'stores')
                store_list.append(entry)

    return store_list


def fetch(level=1, data=None, user='root', passwd=''):
    def func(data, level):
        """
        :param data:
        :param level: 0：国家；1：城市；2：商店列表
        """
        if level == 0:
            # 商店
            return [{'func': None, 'data': s} for s in fetch_stores(data)]
        else:
            return []

    # Walk from the root node, where level == 1.
    if data is None:
        data = {'url': 'http://www.mulberry.com/about/store_locator.asp',
                'brand_id': 10270, 'brandname_e': u'Mulberry', 'brandname_c': u'迈宝瑞'}

    global db
    db = cm.StoresDb()
    db.connect_db(user=user, passwd=passwd)
    db.execute(u'DELETE FROM %s WHERE brand_id=%d' % ('stores', data['brand_id']))

    results = cm.walk_tree({'func': lambda data: func(data, 0), 'data': data})
    db.disconnect_db()

    return results

