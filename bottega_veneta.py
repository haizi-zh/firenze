# coding=utf-8
import json
import string
import re
import common as cm
import geosense as gs

__author__ = 'Zephyre'

db = None
log_name = 'bottega_veneta_log.txt'


def fetch_stores(data):
    url = data['url']
    try:
        body = cm.get_data(url)
    except Exception, e:
        cm.dump('Error in fetching stores: %s' % url, log_name)
        return ()

    m = re.search(ur'var\s+storelocatorMarkers\s*=\s*\[([^\[\]]+)\]', body, re.S)
    raw = json.loads(m.group(1))
    store_list = []
    for s in raw.values():
        entry = cm.init_store_entry(data['brand_id'], data['brandname_e'], data['brandname_c'])
        entry[cm.country_e] = cm.html2plain(s['country']).strip().upper()
        entry[cm.city_e] = cm.html2plain(s['city']).strip().upper()
        entry[cm.name_e] = cm.html2plain(s['title']).strip()
        entry[cm.addr_e] = cm.reformat_addr(s['address'])
        latlong = s['latlong']
        if isinstance(latlong, dict):
            try:
                entry[cm.lat] = string.atof(latlong['lat'])
            except (ValueError, KeyError, TypeError) as e:
                cm.dump('Error in fetching lat-lng: %s' % str(e), log_name)
            try:
                entry[cm.lng] = string.atof(latlong['lng'])
            except (ValueError, KeyError, TypeError) as e:
                cm.dump('Error in fetching lat-lng: %s' % str(e), log_name)
        entry[cm.tel] = s['store_phone'].strip()
        entry[cm.email] = s['store_email'].strip()
        entry[cm.hours] = cm.reformat_addr(s['store_hours'])

        gs.field_sense(entry)
        ret = gs.addr_sense(entry[cm.addr_e], entry[cm.country_e])
        if ret[1] is not None and entry[cm.province_e] == '':
            entry[cm.province_e] = ret[1]
        if ret[2] is not None and entry[cm.city_e] == '':
            entry[cm.city_e] = ret[2]
        gs.field_sense(entry)

        cm.dump('(%s / %d) Found store: %s, %s (%s, %s)' % (data['brandname_e'], data['brand_id'],
                                                            entry[cm.name_e], entry[cm.addr_e],
                                                            entry[cm.country_e],
                                                            entry[cm.continent_e]), log_name)
        db.insert_record(entry, 'stores')
        store_list.append(entry)

    return tuple(store_list)


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
            return ()

    # Walk from the root node, where level == 1.
    if data is None:
        data = {'url': 'http://www.bottegaveneta.com/experience/us/pages/store-locator/',
                'brand_id': 10049, 'brandname_e': u'Bottega Veneta', 'brandname_c': u'宝缇嘉'}

    global db
    db = cm.StoresDb()
    db.connect_db(user=user, passwd=passwd)
    db.execute(u'DELETE FROM %s WHERE brand_id=%d' % ('stores', data['brand_id']))

    results = cm.walk_tree({'func': lambda data: func(data, 0), 'data': data})
    db.disconnect_db()
    cm.dump('Done!', log_name)

    return results


